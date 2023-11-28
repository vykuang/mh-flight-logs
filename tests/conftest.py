"""
Based on suggestions from https://www.cosmicpython.com/blog/2020-01-25-testing_external_api_calls.html,
build an adapter, i.e. wrapper for our external API instead. This should
disentangle our business logic from API integration. Abstracting the API call
away exposes readable methods for us to call in testing code
"""
import pytest
import json

# @pytest.fixture(autouse=True)
# def no_requests(monkeypatch):
#     """remove requests.sessions.Session.request for all tests"""
#     monkeypatch.delattr("requests.sessions.Session.request")


class AviationAPI:
    API_URL = "https://api.aviationstack.com"


@pytest.fixture
def sample_payload():
    with open("tests/data/sample_flight_response.json") as f:
        return json.load(f)


@pytest.fixture
def sample_error():
    with open("tests/data/sample_error_response.json") as f:
        return json.load(f)
