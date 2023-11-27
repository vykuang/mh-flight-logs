import requests
import pytest
import json
from asean_flight_logs import main


class MockResponse:
    @staticmethod
    # it's a plain old func tucked inside a class.
    # call with MockResponse().json() to return our json
    # Useful here since our mocked object do not need any
    # class/instance context to return the json response
    def json():
        with open("tests/data/sample_flight_response.json") as f:
            response = json.load(f)
        return response

    @staticmethod
    def raise_for_status():
        return


# monkeypatched requests.get moved to fixture
@pytest.fixture
def mock_response(monkeypatch):
    """Requests.get() mocked to return the above json"""

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests.Session, "get", mock_get)


# our test uses the custom fixture instead of monkeypatch directly
def test_get_json(mock_response, tmp_path):
    res = main.get_all_delays(
        airline_iata="mh", str_date="2000-01-01", json_dir=tmp_path
    )
    assert len(res) == 200


def test_request_retry():
    assert True


# def test_todo_api():
#    response = requests.get("http://jsonplaceholder.typicode.com/todos")
#    assert response.ok
