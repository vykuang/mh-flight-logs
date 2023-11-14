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
from datetime import date, datetime, timezone, timedelta
from time import sleep
from collections.abc import MutableMapping
import tweepy
import argparse
import logging
from sys import stdout
import jinja2
import tomllib

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(funcName)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    handlers=[logging.StreamHandler(stdout)],
)
logger = logging.getLogger(__name__)

AV_API_KEY = os.getenv("AVIATION_API_KEY", "")
AV_API_URL = "http://api.aviationstack.com/v1/"
FLIGHT_API_URL = AV_API_URL + "flights"

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

toml_path = Path("pyproject.toml")
with open(toml_path, "rb") as f:
    config = tomllib.load(f)

DB_NAME = config["sqlite"]["db_name"]
TBL_NAME = config["sqlite"]["tbl_name"]
JSON_COL = config["sqlite"]["json_col"]


def write_local_json(
    api_response: dict,
    json_dir: Path,
    str_date: str,
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
    str_date: str,
    json_dir: str,
    limit: int = 100,
    airline: str = "Malaysia Airlines",
    min_delay: int = 1,
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
    logger.info(f"Retrieving delayed flights for {str_date}")
    while not total or retrieved < total:
        sleep(0.5)
        logger.info(f"retrieving {retrieved}th to {retrieved + limit}th")
        params = {
            "access_key": AV_API_KEY,  # retrieved from .env, global scope
            "offset": retrieved,
            "limit": limit,
            "airline_name": airline,
            # "min_delay_arr": min_delay,
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
        response = response.json()
        logger.debug(f"retrieved {retrieved}th to {retrieved + limit}th")
        json_path = write_local_json(
            response, json_dir=json_dir, str_date=str_date, offset=retrieved
        )
        responses.extend(response["data"])
        retrieved += response["pagination"]["count"]
        if not total:
            # First request; get total count
            total = response["pagination"]["total"]
            logger.info(f"Total records count: {total}")
            if total == 0:
                # prevent infinite loop if there are no records retrieved
                logger.error("Zero records retrieved; exiting")
                break
    return responses


def execute_template_sql(
    db_conn: sqlite3.Connection,
    env: jinja2.Environment,
    template: str,
    params: dict,
    data: list = None,
):
    """
    Renders the jinja templated sql and executes,
    returning results if any
    """
    sql = env.get_template(template).render(params)
    logger.debug(f"rendered SQL:\n{sql}")
    with db_conn:
        if data:
            db_conn.executemany(sql, data)
            return None
        else:
            # executescript did not return any results
            if "CREATE" in sql or "INSERT INTO" in sql:
                db_conn.executescript(sql)
            else:
                return db_conn.execute(sql)


def dict_factory(cursor, row):
    """
    cursor: sqlite3 cursor object
    row: tuple from query result
    returns the tuple row as dict
    """
    # .description attr returns a 7-tuple; only 1st is the col name
    fields = [descr[0] for descr in cursor.description]
    return {field: val for field, val in zip(fields, row)}


def main(
    str_date: str,
    data_dir: Path = Path("data"),
    template_dir: Path = Path("templates"),
    local_json: bool = False,
    local_tweet: bool = False,
    loglevel: str = "info",
):
    """
    Tweets how late malaysia airline was today
    Searches through all flights scheduled to arrive today
    Scheduled to run daily at 23:50:00 UTC

    Parameters:
    str_date: str
        date in yyyy-mm-dd format

    data_dir: Path
        mount point for container. program will look for and store json responses
        in data_dir / "responses", and sqlite db in data_dir / "flights.db"

    local_json: bool
        if True, program will look for json responses in data_dir / "responses"
        instead of requesting API

    local_tweet: bool
        if True, prints to terminal instead of posting to twitter

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
                entries.extend(flight_page["data"])

    else:
        logger.info("Requesting flight API")
        entries = get_all_delays(str_date=str_date, json_dir=json_dir)

    params = dict(
        tbl_name=TBL_NAME,
        json_col=JSON_COL,
    )
    # instantiate db conn and jinja env
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    db_path = data_dir / "flights.db"
    logger.debug(f"connecting to sqlite db @ {db_path}")
    db_exists = db_path.exists()
    db_conn = sqlite3.connect(db_path)
    if not db_exists:
        logger.info(f"{db_path} does not exist, initializing...")
        execute_template_sql(db_conn, env, "create.sql", params)

    # UPSERT data
    # restructure as list of tuples
    flights = [(json.dumps(flight),) for flight in entries]
    # db_conn.executemany(f"INSERT OR REPLACE INTO {TBL_NAME} ({JSON_COL}) VALUES( ? )", flights)
    execute_template_sql(db_conn, env, "insert.sql", params, flights)
    # rows will be returned as a dict, with col names as keys
    db_conn.row_factory = dict_factory

    logger.debug("Querying database...")
    params = dict(tbl_name=TBL_NAME, json_col=JSON_COL, str_date=str_date)
    agg = execute_template_sql(db_conn, env, "agg.sql", params)
    delays = execute_template_sql(db_conn, env, "delayed_json.sql", params)
    # tweet
    oauth1_client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
    )
    total, num_delay, avg_delay = next(agg).values()
    pt1 = f"{num_delay}/{total} MH flights were late on {str_date}"
    pt2 = f"by an average of {avg_delay:.0f} min."
    delays_in_sentences = "\n" + "\n".join(
        [
            f"{i+1} {d['flight_num']}: {d['start']} to {d['dest']}, {d['delay']} min"
            for i, d in enumerate(delays)
        ]
    )
    tweet = " ".join([pt1, pt2, delays_in_sentences]).replace("None", "N/A")
    if (tweet_chars := len(tweet)) > 280:
        logging.warning(f"Truncating tweet from {tweet_chars} to 280 chars")
        tweet = tweet[:280]
    logger.debug(f"tweet length: {len(tweet)}")
    db_conn.close()
    if local_tweet:
        logger.info(f"offline tweet:\n{tweet}")
    else:
        try:
            t_response = oauth1_client.create_tweet(text=tweet, user_auth=True)
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
        "--flight_date",
        type=str,
        default=str(datetime.now(tz=timezone.utc).date() - timedelta(days=1)),
        help="Date in yyyy-mm-dd format to look for delayed flights; best with --local_json",
    )
    opt(
        "--data_dir",
        type=Path,
        default=Path("/data"),
        help="Directory to store json responses and sqlite db",
    )
    opt(
        "--template_dir",
        type=Path,
        default=Path("/templates"),
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
        args.flight_date,
        args.data_dir,
        args.template_dir,
        args.local_json,
        args.local_tweet,
        args.loglevel,
    )
