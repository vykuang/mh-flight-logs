import requests
import responses
from responses import registries
import json
from asean_flight_logs import main
from datetime import datetime, timezone
import tomllib
from pathlib import Path
from urllib3 import Retry
import re

toml_path = Path("pyproject.toml")
with open(toml_path, "rb") as f:
    config = tomllib.load(f)

DB_NAME = config["sqlite"]["db_name"]
TBL_NAME = config["sqlite"]["tbl_name"]
JSON_COL = config["sqlite"]["json_col"]
AV_API_URL = config["aviationstack"]["base_url"]
AV_API_ENDPOINT = config["aviationstack"]["flight"]


@responses.activate
def test_aviation_api(tmp_path):
    with open("tests/data/sample_flight_response.json") as f:
        sample_payload = json.load(f)
    # register via 'Response' obj
    # resp1 = responses.Response(
    #     method='GET',
    #     url="http://api.aviationstack.com",
    #     status=200,
    #     body=sample_payload
    # )
    # # .add() to register
    # responses.add(resp1)
    responses.add(
        responses.GET,
        # takes a regex compiled object to match
        re.compile("http://api.aviationstack.com/.*"),
        json=sample_payload,
        status=200,
    )

    sample_flights = main.get_all_delays(
        airline_iata="mh",
        str_date=datetime.now(tz=timezone.utc).date(),
        json_dir=tmp_path,
    )
    assert len(sample_flights) == 200


@responses.activate(registry=registries.OrderedRegistry)
def test_max_retries():
    """From docs"""
    url = "https://example.com"
    rsp1 = responses.get(url, body="Error", status=500)
    rsp2 = responses.get(url, body="Error", status=500)
    rsp3 = responses.get(url, body="Error", status=501)
    rsp4 = responses.get(url, body="OK", status=200)

    session = requests.Session()

    adapter = requests.adapters.HTTPAdapter(
        max_retries=Retry(
            total=4,
            backoff_factor=0.1,
            status_forcelist=[500, 501],
            allowed_methods=["GET", "POST", "PATCH"],
        )
    )
    session.mount("https://", adapter)

    resp = session.get(url)

    assert resp.status_code == 200
    assert rsp1.call_count == 1
    assert rsp2.call_count == 1
    assert rsp3.call_count == 1
    assert rsp4.call_count == 1
