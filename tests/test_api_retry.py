import requests
import pytest
from asean_flight_logs import main


class MockResponse:
    @staticmethod
    def json():
        return {
            "data": "mock_response",
            "pagination": {"count": 100, "total": 200},
        }

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
    monkeypatch.setattr(main, "write_local_json", mock_get)


# our test uses the custom fixture instead of monkeypatch directly
def test_get_json(mock_response):
    res = main.get_all_delays("aa", "2000-01-01", "data")
    assert res == "mock_response"


def test_request_retry():
    assert True


def test_todo_api():
    response = requests.get("http://jsonplaceholder.typicode.com/todos")
    assert response.ok
