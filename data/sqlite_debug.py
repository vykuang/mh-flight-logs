#! /usr/bin/env python
import sqlite3
from datetime import date


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
    flight_num = f"flight{sep}iata"
    a_port = f"arrival{sep}airport"
    a_delay = f"arrival{sep}delay"
    d_port = f"departure{sep}airport"
    d_delay = f"departure{sep}delay"
    d_sched = f"departure{sep}scheduled"

    agg_sql = f"""
        SELECT COUNT(*) num_delayed,
        AVG({a_delay}) avg_delay
        FROM {tbl_name}
        WHERE DATE({d_sched}) = '{str_date}'
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
        WHERE DATE({d_sched}) = '{str_date}'
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
            f"{d[flight_num]} from {d[a_port]} to {d[d_port]} by {int(d[a_delay])} min"
            for d in delays
        ]
    )
    pt1 = f"On {str_date}, {num_delay} MH flights were delayed"
    pt2 = f"by an average of {avg_delay:.0f} min."
    pt3 = f"Most delayed flights: {delays_in_sentences}"
    return " ".join([pt1, pt2, pt3])


if __name__ == "__main__":
    print("opening flights.db")
    db_conn = sqlite3.connect("flights.db")
    # print(write_flight_tweet(db_conn))
    curs = db_conn.execute("SELECT * FROM SQLITE_MASTER")
    print(curs.fetchall())
    print("closing flights.db")
    db_conn.close()
    print("closed flights.db")
