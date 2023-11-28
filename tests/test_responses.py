import responses
from responses import registries
from datetime import datetime, timezone
import tomllib
from pathlib import Path
import re

from asean_flight_logs import main

toml_path = Path("pyproject.toml")
with open(toml_path, "rb") as f:
    config = tomllib.load(f)

DB_NAME = config["sqlite"]["db_name"]
TBL_NAME = config["sqlite"]["tbl_name"]
JSON_COL = config["sqlite"]["json_col"]
AV_API_URL = config["aviationstack"]["base_url"]
AV_API_ENDPOINT = config["aviationstack"]["flight"]


@responses.activate
def test_aviation_api(sample_payload, tmp_path):
    # register via 'Response' obj
    # resp1 = responses.Response(
    #     method='GET',
    #     url="http://api.aviationstack.com",
    #     status=200,
    #     body=sample_payload
    # )
    # # .add() to register
    # responses.add(resp1)

    # responses.add(
    #     responses.GET,
    #     # takes a regex compiled object to match
    #     re.compile(f"{AV_API_URL}.*"),
    #     json=sample_payload,
    #     status=200,
    # )
    responses.get(
        re.compile(f"{AV_API_URL}.*"), json=sample_payload, status=200
    )
    sample_flights = main.get_all_delays(
        airline_iata="mh",
        str_date=datetime.now(tz=timezone.utc).date(),
        json_dir=tmp_path,
    )
    assert len(sample_flights) == 200


@responses.activate(registry=registries.OrderedRegistry)
def test_max_retries(sample_payload, sample_error, tmp_path):
    """From docs
    Use OrderedRegistry to maintain order of returned responses
    to test retry mechanism
    """
    url = re.compile(f"{AV_API_URL}.*")
    # shortcut to responses.add(responses.GET, ...)
    rsp1 = responses.get(url, json=sample_error, status=500)
    rsp2 = responses.get(url, json=sample_error, status=502)
    # we end up calling it twice because sample total = 200, and
    # each call retrieves only 100 entries
    rsp3 = responses.get(url, json=sample_payload, status=200)
    rsp4 = responses.get(url, json=sample_payload, status=200)

    sample_flights = main.get_all_delays(
        airline_iata="mh",
        str_date=datetime.now(tz=timezone.utc).date(),
        json_dir=tmp_path,
    )

    assert len(sample_flights) == 200
    assert rsp1.call_count == 1
    assert rsp2.call_count == 1
    assert rsp3.call_count == 1
    assert rsp4.call_count == 1
