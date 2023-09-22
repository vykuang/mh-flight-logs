#! /usr/bin/env python
import os
import requests
import sqlite3
from sqlite3 import ProgrammingError
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import date
from time import sleep
from collections.abc import MutableMapping
import tweepy
import argparse

env_path = Path("../.env")
load_dotenv(env_path)
av_api_key = os.getenv("AVIATION_API_KEY", "")
av_api_url = "http://api.aviationstack.com/v1/"
flight_api_url = av_api_url + "flights"

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")


def get_flight_api(
    offset: int = 0,
    limit: int = 100,
    airline: str = "Malaysia Airlines",
    min_delay: int = 1,
    flight_api_url="http://api.aviationstack.com/v1/flights",
    timeout: float = 10.0,
) -> dict:
    """
    Requests aviationstack API for flight data
    Returns responses in a dict
    """
    params = {
        "access_key": av_api_key,  # retrieved from .env, global scope
        "offset": offset,
        "limit": limit,
        "airline_name": airline,
        "min_delay_arr": min_delay,
    }
    result = requests.get(flight_api_url, params, timeout=timeout)
    return result.json()


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
    local_json_path = json_dir / f"flight-{str_date}-{offset}-{offset+limit}.json"
    with open(local_json_path, "w") as j:
        json.dump(api_response, j)
        print(f"saved to {local_json_path}")
    return local_json_path


def get_all_delays(
    json_dir: str,
    limit: int = 100,
    airline: str = "Malaysia Airlines",
    min_delay: int = 1,
    str_date: str = str(date.today()),
    flight_api_url="http://api.aviationstack.com/v1/flights",
):
    responses = []
    retrieved = total = 0
    while not total or retrieved < total:
        sleep(0.5)
        print(f"retrieving {retrieved}th to {retrieved + limit}th")
        responses.append(get_flight_api(offset=retrieved, limit=limit))
        # save response
        json_path = write_local_json(
            responses[-1], json_dir=json_dir, str_date=str_date, offset=retrieved
        )
        retrieved += responses[-1]["pagination"]["count"]
        if not total:
            total = responses[0]["pagination"]["total"]
            print(f"Total records count: {total}")
    return responses


def json_flatten(data: dict, parent_key="", sep="_"):
    """
    Normalizes json, if nested
    """
    items = []
    for key, val in data.items():
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(val, MutableMapping):
            items.extend(json_flatten(val, parent_key=new_key, sep=sep).items())
        else:
            items.append((new_key, val))

    # creates {key: val} from (key, val) tuple
    return dict(items)


def issubstring(text: str, checklist, sep="__") -> bool:
    """
    Returns True for overlapped keys
    """
    for check in checklist:
        if text + sep in check:
            return True
    return False


def find_json_schema(entries: list[dict]) -> list:
    fields = set()
    for entry in entries:
        fields.update(entry.keys())

    fields_uniq = [field for field in fields if not issubstring(field, fields)]
    return fields_uniq


def create_table(
    schema: list,
    db_conn: sqlite3.Connection,
    tbl_name: str = "import_flight_records",
    sep="__",
):
    """
    Creates the table in sqlite if it doesn't already exist
    """
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
        print(e)


def write_flight_tweet(
    db_conn: sqlite3.Connection,
    tbl_name: str = "import_flight_records",
    str_date: str = str(date.today()),
    sep: str = "__",
) -> str:
    """
    Queries the flight records database to write the tweet
    Prepared queries makes some assumption about the table schema
    1. follows aviationstack flights endpoint
    1. flattened, with the same sep character
    """
    # defining column names inside db
    flight_num = f"flight{sep}iata"
    a_port = f"arrival{sep}airport"
    a_delay = f"arrival{sep}delay"
    a_sched = f"arrival{sep}scheduled"
    d_port = f"departure{sep}airport"
    d_delay = f"departure{sep}delay"
    d_sched = f"departure{sep}scheduled"

    agg_sql = f"""
        SELECT COUNT(*) num_delayed,
        AVG({a_delay}) avg_delay
        FROM {tbl_name}
        WHERE DATE({a_sched}) = '{str_date}'
    """

    most_delayed_sql = f"""
        SELECT 
            ROW_NUMBER() OVER (ORDER BY CAST({a_delay} AS INTEGER) DESC) delay_rank,
            {flight_num},
            REPLACE(
            REPLACE(
            REPLACE({a_port}, ' International Airport', '')
            , ' International', '')
            , ' Airport', '') AS {a_port},
            REPLACE(
            REPLACE(
            REPLACE({d_port}, ' International Airport', '')
            , ' International', '')
            , ' Airport', '') AS {d_port},
            {a_delay}
        FROM {tbl_name}
        WHERE DATE({a_sched}) = '{str_date}'
        ORDER BY delay_rank
        LIMIT 3;
    """
    with db_conn:
        curs = db_conn.execute(agg_sql)
        num_delay, avg_delay = curs.fetchall()[0].values()
        curs = db_conn.execute(most_delayed_sql)
        delays = curs.fetchall()

    delays_in_sentences = "\n" + "\n".join(
        [
            f"{d[flight_num]} from {d[d_port]} to {d[a_port]} by {int(d[a_delay])} min"
            for d in delays
        ]
    )
    pt1 = f"On {str_date}, {num_delay} MH flights were delayed"
    pt2 = f"by an average of {avg_delay:.0f} min."
    pt3 = f"Most delayed flights: {delays_in_sentences}"
    return " ".join([pt1, pt2, pt3])


def main(
    json_dir: Path,
    db_path: Path,
    str_date: str = str(date.today()),
    use_local: bool = False,
):
    """
    Tweets how late malaysia airline was today
    Searches through all flights scheduled to arrive today
    Scheduled to run at 11:50 PM
    """
    # flatten the nested dicts in the response jsons
    if use_local:
        entries = []
        json_paths = json_dir.glob(f"flight-{str_date}-*.json")
        for json_file in json_paths:
            with open(json_file) as j:
                flight_page = json.load(j)
                flat = [
                    json_flatten(nested, sep="__") for nested in flight_page["data"]
                ]
                entries.extend(flat)

    else:
        responses = get_all_delays(str_date=str_date, json_dir=json_dir)
        # collecting records from all responses
        entries = [
            json_flatten(nested, sep="__")
            for response in responses
            for nested in response["data"]
        ]

    # creating schema from json fields
    schema = find_json_schema(entries)
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
    payload = write_flight_tweet(db_conn, str_date=str_date)

    t_response = oauth1_client.create_tweet(text=payload, user_auth=True)
    print(f"link: https://twitter.com/user/status/{t_response.data['id']}")
    print(f"text: {t_response.data['text']}")


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
        help="Date in yyyy-mm-dd format, to look for late flights; best with --use_local",
    )
    opt(
        "--json_dir",
        type=Path,
        default=Path("../data/responses"),
        help="directory to store json responses",
    )
    opt(
        "--db_path",
        type=Path,
        default=Path("../data/flights.db"),
        help="Path to sqlite database",
    )
    opt(
        "--use_local",
        action="store_true",
        default=False,
        help="Look in json_dir for saved local responses instead of requesting from API",
    )
    args = parser.parse_args()
    main(args.json_dir, args.db_path, args.arrival_date, args.use_local)
