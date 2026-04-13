import pytest

from launchprogress.duration import format_time, parse_duration


class TestParseDuration:
    def test_bare_seconds(self):
        assert parse_duration("90") == 90

    def test_seconds_suffix(self):
        assert parse_duration("30s") == 30

    def test_minutes(self):
        assert parse_duration("5m") == 300

    def test_hours(self):
        assert parse_duration("1h") == 3600

    def test_hours_minutes(self):
        assert parse_duration("1h30m") == 5400

    def test_minutes_seconds(self):
        assert parse_duration("25m30s") == 1530

    def test_full_combo(self):
        assert parse_duration("1h30m15s") == 5415

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_duration("abc")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_duration("")


class TestFormatTime:
    def test_seconds_only(self):
        assert format_time(45) == "45s"

    def test_minutes_seconds(self):
        assert format_time(125) == "2m 05s"

    def test_hours(self):
        assert format_time(3661) == "1h 01m 01s"

    def test_zero(self):
        assert format_time(0) == "0s"

    def test_exact_minute(self):
        assert format_time(60) == "1m 00s"

    def test_exact_hour(self):
        assert format_time(3600) == "1h 00m 00s"
