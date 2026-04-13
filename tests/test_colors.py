from unittest.mock import patch

from launchprogress.colors import (
    TRAFFIC_COLORS,
    color_for_fraction,
    color_for_led,
    rgb_to_hex,
    selection_color_for_minute,
)


class TestRgbToHex:
    def test_black(self):
        assert rgb_to_hex(0, 0, 0) == "#000000"

    def test_white(self):
        assert rgb_to_hex(255, 255, 255) == "#ffffff"

    def test_red(self):
        assert rgb_to_hex(255, 0, 0) == "#ff0000"


class TestColorForFraction:
    def test_high_fraction_green(self):
        assert color_for_fraction(0.8) == TRAFFIC_COLORS["green"]

    def test_mid_fraction_amber(self):
        assert color_for_fraction(0.4) == TRAFFIC_COLORS["amber"]

    def test_low_fraction_red(self):
        assert color_for_fraction(0.1) == TRAFFIC_COLORS["red"]

    def test_boundary_60(self):
        assert color_for_fraction(0.60) == TRAFFIC_COLORS["amber"]

    def test_above_60(self):
        assert color_for_fraction(0.61) == TRAFFIC_COLORS["green"]

    def test_boundary_25(self):
        assert color_for_fraction(0.25) == TRAFFIC_COLORS["red"]

    def test_above_25(self):
        assert color_for_fraction(0.26) == TRAFFIC_COLORS["amber"]


# Pin brightness to 1.0 so tests don't depend on time of day
@patch("launchprogress.colors.time_of_day_brightness", return_value=1.0)
class TestColorForLed:
    def test_off_when_zero_brightness(self, _mock):
        assert color_for_led(0.5, 0) is None

    def test_off_when_negative_brightness(self, _mock):
        assert color_for_led(0.5, -1) is None

    def test_returns_hex_when_lit(self, _mock):
        result = color_for_led(0.8, 1.0)
        assert result is not None
        assert result.startswith("#")

    def test_full_brightness_green(self, _mock):
        result = color_for_led(0.8, 1.0)
        assert result == rgb_to_hex(0, 200, 0)

    def test_half_brightness(self, _mock):
        result = color_for_led(0.8, 0.5)
        assert result == rgb_to_hex(0, 100, 0)

    def test_amber_cutoff(self, _mock):
        assert color_for_led(0.4, 0.14) is None
        assert color_for_led(0.4, 0.16) is not None

    def test_red_no_cutoff(self, _mock):
        assert color_for_led(0.1, 0.05) is not None

    def test_brightness_capped_at_1(self, _mock):
        assert color_for_led(0.8, 2.0) == color_for_led(0.8, 1.0)


class TestSelectionColorForMinute:
    def test_first_band(self):
        assert selection_color_for_minute(5) == (0, 200, 0)

    def test_second_band(self):
        assert selection_color_for_minute(15) == (0, 200, 100)

    def test_last_band(self):
        assert selection_color_for_minute(65) == (200, 0, 200)
