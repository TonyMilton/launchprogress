import time
from unittest.mock import MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from timer import create_app


def make_mock_led():
    led = MagicMock()
    # mock needs this to survive repeated del led.color
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

    # clean up any running timer before teardown
    state = app.state.timer
    if state._running:
        state._cancel = True
        if state.thread:
            state.thread.join(timeout=3)


class TestTimerLifecycle:
    def test_full_lifecycle(self, client):
        resp = client.get("/timer")
        assert resp.json()["running"] is False

        resp = client.post("/timer", json={"minutes": 60})
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"

        resp = client.get("/timer")
        data = resp.json()
        assert data["running"] is True
        assert data["remaining_seconds"] > 3500

        resp = client.delete("/timer")
        assert resp.json()["status"] == "cancelled"

        resp = client.get("/timer")
        assert resp.json()["running"] is False

    def test_start_cancel_restart(self, client):
        client.post("/timer", json={"minutes": 10})
        client.delete("/timer")

        resp = client.post("/timer", json={"minutes": 5})
        assert resp.status_code == 200
        assert resp.json()["minutes"] == 5.0

        client.delete("/timer")

    def test_double_cancel(self, client):
        client.post("/timer", json={"minutes": 10})
        client.delete("/timer")

        resp = client.delete("/timer")
        assert resp.status_code == 404

    def test_double_start(self, client):
        client.post("/timer", json={"minutes": 10})
        resp = client.post("/timer", json={"minutes": 5})
        assert resp.status_code == 409

        client.delete("/timer")


class TestTimerCountdown:
    def test_remaining_decreases(self, client):
        client.post("/timer", json={"minutes": 60})

        resp1 = client.get("/timer")
        t1 = resp1.json()["remaining_seconds"]

        time.sleep(0.3)

        resp2 = client.get("/timer")
        t2 = resp2.json()["remaining_seconds"]

        assert t2 < t1

        client.delete("/timer")

    def test_short_timer_completes(self, client):
        client.post("/timer", json={"minutes": 0.05})  # 3 seconds

        # wait for timer + completion animation to finish
        time.sleep(10)

        resp = client.get("/timer")
        assert resp.json()["running"] is False


class TestValidation:
    def test_missing_body(self, client):
        resp = client.post("/timer")
        assert resp.status_code == 422

    def test_wrong_type(self, client):
        resp = client.post("/timer", json={"minutes": "five"})
        assert resp.status_code == 422

    def test_zero(self, client):
        resp = client.post("/timer", json={"minutes": 0})
        assert resp.status_code == 400

    def test_negative(self, client):
        resp = client.post("/timer", json={"minutes": -10})
        assert resp.status_code == 400

    def test_fractional_minutes(self, client):
        resp = client.post("/timer", json={"minutes": 0.5})
        assert resp.status_code == 200
        assert resp.json()["display"] == "30s"
        client.delete("/timer")


class TestLaunchpadInteraction:
    def test_leds_set_on_start(self, client, mock_launchpad):
        client.post("/timer", json={"minutes": 60})
        time.sleep(0.3)

        assert mock_launchpad.grid.led.called

        client.delete("/timer")

    def test_leds_cleared_on_cancel(self, client, mock_launchpad):
        client.post("/timer", json={"minutes": 60})
        time.sleep(0.2)

        mock_launchpad.grid.led_range.reset_mock()
        client.delete("/timer")

        assert mock_launchpad.grid.led_range.called
