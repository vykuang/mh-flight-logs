#!/usr/bin/env python
import os
import requests
from urllib3.util import Retry
from requests import Session, HTTPError
from requests.adapters import HTTPAdapter
from requests.exceptions import ReadTimeout
import sqlite3
from sqlite3 import ProgrammingError
import json
from pathlib import Path
from datetime import date, datetime
from time import sleep
from collections.abc import MutableMapping
import tweepy
import argparse
import logging
from sys import stdout
import jinja2

AV_API_KEY = os.getenv("AVIATION_API_KEY", "")
AV_API_URL = "http://api.aviationstack.com/v1/"
FLIGHT_API_URL = AV_API_URL + "flights"

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(funcName)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    handlers=[logging.StreamHandler(stdout)],
)
logger = logging.getLogger(__name__)


def write_local_json(
    api_response: dict,
    json_dir: Path,
    str_date: str = str(date.today()),
    offset: int = 0,
    limit: int = 100,
):
    """
    Saves the flight api response as json, to be uploaded to a data lake
    """
    if not json_dir.exists():
        json_dir.mkdir(parents=True)
    local_json_path = json_dir / f"flight-{str_date}-{offset}-{offset+limit}.json"
    logger.info(f"saving to {local_json_path}")
    with open(local_json_path, "w") as j:
        json.dump(api_response, j)
        logger.debug(f"saved to {local_json_path}")
    return local_json_path


def get_all_delays(
    json_dir: str,
    limit: int = 100,
    airline: str = "Malaysia Airlines",
    min_delay: int = 1,
    str_date: str = str(date.today()),
):
    sesh = Session()
    adapter = HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
            # allowed_methods={"POST"},
        )
    )
    sesh.mount(AV_API_URL, adapter)
    responses = []
    retrieved = total = 0
    while not total or retrieved < total:
        sleep(0.5)
        logger.info(f"retrieving {retrieved}th to {retrieved + limit}th")
        params = {
            "access_key": AV_API_KEY,  # retrieved from .env, global scope
            "offset": retrieved,
            "limit": limit,
            "airline_name": airline,
            "min_delay_arr": min_delay,
        }
        try:
            response = sesh.get(
                url=FLIGHT_API_URL,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
        except HTTPError as exc:
            logger.error(f"HTTP Error: \n{exc}")

        except ReadTimeout as e:
            logger.error(
                f"Timeout retrieving {retrieved}th to {retrieved + limit}th:\n{e}"
            )
        # save response
        logger.debug(f"retrieved {retrieved}th to {retrieved + limit}th")
        responses.append(response.json())
        # save response
        json_path = write_local_json(
            responses[-1], json_dir=json_dir, str_date=str_date, offset=retrieved
        )
        retrieved += responses[-1]["pagination"]["count"]
        if not total:
            total = responses[0]["pagination"]["total"]
            logger.info(f"Total records count: {total}")
    return responses


def create_table(
    schema: list,
    db_conn: sqlite3.Connection,
    tbl_name: str = "import_flight_records",
    sep="__",
):
    """
    Creates the table in sqlite if it doesn't already exist
    """
    logger.debug("Executing DDL")
    pk = [
        ["flight", "iata"],
        ["departure", "iata"],
        ["departure", "scheduled"],
        ["arrival", "iata"],
    ]
    pk = [sep.join(field) for field in pk]
    if not all([key in schema for key in pk]):
        raise ValueError(f"one of primary keys: {pk} not in schema list")

    ddl = f"""
    CREATE TABLE IF NOT EXISTS {tbl_name} (
        {", ".join([f"{field} TEXT DEFAULT NULL" for field in schema])},
        PRIMARY KEY ({", ".join(pk)})
    )"""
    db_conn.execute(ddl)
    logger.debug("DDL executed")


def dict_factory(cursor, row):
    """
    cursor: sqlite3 cursor object
    row: tuple from query result
    returns the tuple row as dict
    """
    # .description attr returns a 7-tuple; only 1st is the col name
    fields = [descr[0] for descr in cursor.description]
    return {field: val for field, val in zip(fields, row)}


def upsert_entries(
    entries: dict,
    db_conn: sqlite3.Connection,
    tbl_name: str = "import_flight_records",
):
    """
    UPSERT data into the import table
    There is no UPSERT function that replaces INSERT;
    rather it's an ON CONFLICT DO clause that can be added to an INSERT
    statement to handle unique key constraints
    """
    # retrieve the table column order for correct insertion
    with db_conn:
        curs = db_conn.execute(f"pragma table_info('{tbl_name}')")
        tbl_info = curs.fetchall()
    col_names = [col_info["name"] for col_info in tbl_info]
    logger.debug(f"{len(col_names)} columns retrieved from tbl_info")
    # inserting nulls where the field is empty
    entries_expanded = (
        {field: entry.get(field) for field in col_names} for entry in entries
    )
    cols_placeholder = ", ".join([f":{field}" for field in col_names])
    try:
        with db_conn:
            db_conn.executemany(
                f"INSERT OR REPLACE INTO {tbl_name} VALUES({cols_placeholder})",
                entries_expanded,
            )
    except ProgrammingError as e:
        logging.critical(e)
    logger.info(f"{len(entries)} entries UPSERTed into database")


def write_flight_tweet(
    db_conn: sqlite3.Connection,
    tbl_name: str = "import_flight_records",
    str_date: str = str(date.today()),
    sep: str = "__",
    num_delay: int = 3,
    template_dir: Path = Path("templates"),
) -> str:
    """
    Queries the flight records database to write the tweet
    Prepared queries makes some assumption about the table schema
    - follows aviationstack flights endpoint
    - flattened, with the same sep character

    Returns a string populated with the query result
    """
    # defining column names inside db for populating the tweet
    flight_num = f"flight{sep}iata"
    a_port = f"arrival{sep}airport"
    a_delay = f"arrival{sep}delay"
    a_sched = f"arrival{sep}scheduled"
    d_port = f"departure{sep}airport"

    # params to render the query template
    params = dict(
        flight_num=flight_num,
        a_port=a_port,
        a_delay=a_delay,
        a_sched=a_sched,
        d_port=d_port,
        num_delay=3,
        str_date=str_date,
        tbl_name=tbl_name,
    )
    logger.debug("Instantiating jinja environment")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    logger.debug(
        f"Searching for sql templates from {(Path.cwd() / template_dir).resolve()}"
    )
    agg_sql = env.get_template("agg.sql").render(params)
    logger.debug(f"rendered agg_sql:\n{agg_sql}")
    delayed_sql = env.get_template("delayed.sql").render(params)
    logger.debug(f"rendered delayed_sql:\n{delayed_sql}")
    logger.debug("Querying database...")
    with db_conn:
        curs = db_conn.execute(agg_sql)
        num_delay, avg_delay = curs.fetchall()[0].values()
        curs = db_conn.execute(delayed_sql)
        delays = curs.fetchall()
    logger.info("DB query executed")
    logger.debug("Query result:\n", delays)
    delays_in_sentences = "\n" + "\n".join(
        [
            f"{i+1} {d[flight_num]}: {d[d_port]} to {d[a_port]}, {int(d[a_delay])} min"
            for i, d in enumerate(delays)
        ]
    )
    pt1 = f"{num_delay} MH flights were late on {str_date}"
    pt2 = f"by an average of {avg_delay:.0f} min."
    tweet = " ".join([pt1, pt2, delays_in_sentences])
    if (tweet_chars := len(tweet)) > 280:
        logging.warning(f"Truncating tweet from {tweet_chars} to 280 chars")
        tweet = tweet[:280]
    logger.debug(f"tweet length: {len(tweet)}")
    return tweet


def main(
    str_date: str = str(date.today()),
    data_dir: Path = Path("data"),
    template_dir: Path = Path("templates"),
    local_json: bool = False,
    local_tweet: bool = False,
    loglevel: str = "info",
):
    """
    Tweets how late malaysia airline was today
    Searches through all flights scheduled to arrive today
    Scheduled to run daily at 23:50:00

    Parameters:
    str_date: str
        date in yyyy-mm-dd format

    data_dir: Path
        mount point for container. program will look for and store json responses
        in data_dir / "responses", and sqlite db in data_dir / "flights.db"

    local_json: bool
        if True, program will look for json responses in data_dir / "responses"
        instead of requesting API

    loglevel: str
        one of default log levels; lower or uppercase accepted
    """
    num_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(num_level, int):
        raise ValueError(f"Invalid log level {loglevel}")
    logger.setLevel(num_level)
    logger.addHandler(logging.FileHandler(data_dir / "debug.log"))
    logger.debug(f"log level: {loglevel}")
    logger.info(f"Execution time: {datetime.now()}")
    logger.info(f"Searching flights from {str_date}\nUse local json: {local_json}")
    # flatten the nested dicts in the response jsons
    json_dir = data_dir / "responses"
    if local_json:
        entries = []
        json_paths = json_dir.glob(f"flight-{str_date}-*.json")
        for json_file in json_paths:
            logger.debug(f"looking for {json_file}")
            with open(json_file) as j:
                flight_page = json.load(j)
                flat = [
                    json_flatten(nested, sep="__") for nested in flight_page["data"]
                ]
                entries.extend(flat)

    else:
        logger.info("Requesting flight API")
        responses = get_all_delays(str_date=str_date, json_dir=json_dir)
        # collecting records from all responses
        entries = [
            json_flatten(nested, sep="__")
            for response in responses
            for nested in response["data"]
        ]

    # creating schema from json fields
    schema = find_json_schema(entries)
    logger.debug(f"number of fields: {len(schema)}\nschema:\n{schema}")
    db_path = data_dir / "flights.db"
    logger.debug(f"connecting to sqlite db @ {db_path}")
    db_conn = sqlite3.connect(db_path)

    create_table(schema, db_conn)
    # rows will be returned as a dict, with col names as keys
    db_conn.row_factory = dict_factory
    upsert_entries(entries, db_conn)

    # tweet
    oauth1_client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
    )
    payload = write_flight_tweet(db_conn, str_date=str_date, template_dir=template_dir)
    db_conn.close()
    if local_tweet:
        logger.info(f"offline tweet:\n{payload}")
    else:
        try:
            t_response = oauth1_client.create_tweet(text=payload, user_auth=True)
            logger.info(
                f"link: https://twitter.com/user/status/{t_response.data['id']}"
            )
            logger.info(f"text: {t_response.data['text']}")
        except Exception as e:
            logger.error(f"Tweet failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="./main.py",
        description="Is MH late again? Probably",
        epilog="",
    )
    opt = parser.add_argument
    opt(
        "-d",
        "--arrival_date",
        type=str,
        default=str(date.today()),
        help="Date in yyyy-mm-dd format to look for delayed flights; best with --local_json",
    )
    opt(
        "--data_dir",
        type=Path,
        default=Path("data"),
        help="Directory to store json responses and sqlite db",
    )
    opt(
        "--template_dir",
        type=Path,
        default=Path("templates"),
        help="Directory for sql templates",
    )
    opt(
        "--local_json",
        action="store_true",
        default=False,
        help="Look in json_dir for saved local responses instead of requesting from API",
    )
    opt(
        "--local_tweet",
        action="store_true",
        default=False,
        help="Print tweet to console instead of posting online",
    )
    opt(
        "--loglevel",
        default="info",
        type=str.upper,
        help="log level: debug, info, ..., critical",
    )
    args = parser.parse_args()
    main(
        args.arrival_date,
        args.data_dir,
        args.template_dir,
        args.local_json,
        args.local_tweet,
        args.loglevel,
    )
