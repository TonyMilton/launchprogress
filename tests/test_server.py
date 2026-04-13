from unittest.mock import MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from timer import create_app


def make_mock_led():
    led = MagicMock()
    type(led).color = PropertyMock(return_value=None)
    return led


@pytest.fixture
def mock_launchpad():
    mock_lp = MagicMock()
    mock_lp.grid.led.return_value = make_mock_led()
    mock_lp.grid.led_range.return_value = [make_mock_led() for _ in range(64)]
    return mock_lp


@pytest.fixture
def client(mock_launchpad):
    app = create_app(mock_launchpad)
    with TestClient(app) as c:
        yield c
    state = app.state.timer
    if state._running:
        state._cancel = True
        if state.thread:
            state.thread.join(timeout=3)


class TestGetTimer:
    def test_no_timer(self, client):
        resp = client.get("/timer")
        assert resp.status_code == 200
        assert resp.json()["running"] is False

    def test_completed_field(self, client):
        resp = client.get("/timer")
        assert resp.json()["completed"] is False


class TestPostTimer:
    def test_start(self, client):
        resp = client.post("/timer", json={"minutes": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["minutes"] == 5.0
        assert data["display"] == "5m 00s"

    def test_already_running(self, client):
        client.post("/timer", json={"minutes": 5})
        resp = client.post("/timer", json={"minutes": 10})
        assert resp.status_code == 409

    def test_zero_minutes(self, client):
        resp = client.post("/timer", json={"minutes": 0})
        assert resp.status_code == 400

    def test_negative_minutes(self, client):
        resp = client.post("/timer", json={"minutes": -5})
        assert resp.status_code == 400


class TestDeleteTimer:
    def test_cancel(self, client):
        client.post("/timer", json={"minutes": 60})
        resp = client.delete("/timer")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_no_timer_to_cancel(self, client):
        resp = client.delete("/timer")
        assert resp.status_code == 404


class TestGetTimerRunning:
    def test_shows_remaining(self, client):
        client.post("/timer", json={"minutes": 60})
        resp = client.get("/timer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] is True
        assert data["remaining_seconds"] > 0
        assert "display" in data
