from datetime import datetime

GRID_SIZE = 8
TOTAL_LEDS = GRID_SIZE * GRID_SIZE


def time_of_day_brightness() -> float:
    hour = datetime.now().hour
    if 7 <= hour < 20:
        return 1.0
    elif 20 <= hour < 22:
        return 0.4
    else:
        return 0.15


TRAFFIC_COLORS = {
    "green": (0, 200, 0),
    "amber": (255, 140, 0),
    "red": (255, 0, 0),
}

# Color bands for pad selection display (per-minute)
SELECTION_COLORS = [
    (0, 200, 0),  # green:  0–10 min
    (0, 200, 100),  # teal:   10–20 min
    (0, 100, 200),  # blue:   20–30 min
    (255, 200, 0),  # yellow: 30–40 min
    (255, 100, 0),  # amber:  40–50 min
    (255, 0, 0),  # red:    50–60 min
    (200, 0, 200),  # purple: 60+ min
]


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def color_for_fraction(fraction: float) -> tuple[int, int, int]:
    if fraction > 0.60:
        return TRAFFIC_COLORS["green"]
    elif fraction > 0.25:
        return TRAFFIC_COLORS["amber"]
    else:
        return TRAFFIC_COLORS["red"]


def selection_color_for_minute(minute: float) -> tuple[int, int, int]:
    band = min(int(minute // 10), len(SELECTION_COLORS) - 1)
    return SELECTION_COLORS[band]


def _dim(value: int, scale: float) -> int:
    if value == 0:
        return 0
    return max(1, int(value * scale))


def color_for_led(fraction: float, brightness: float) -> str | None:
    if brightness <= 0:
        return None
    scale = min(brightness, 1.0) * time_of_day_brightness()
    r, g, b = color_for_fraction(fraction)
    if (r, g, b) == TRAFFIC_COLORS["amber"] and scale < 0.15:
        return None
    return rgb_to_hex(_dim(r, scale), _dim(g, scale), _dim(b, scale))
