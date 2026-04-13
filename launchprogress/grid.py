import sys
import time
from contextlib import contextmanager

from lpminimk3 import ButtonEvent, Mode, find_launchpads

from .colors import (
    GRID_SIZE,
    TOTAL_LEDS,
    _dim,
    color_for_led,
    rgb_to_hex,
    selection_color_for_minute,
    time_of_day_brightness,
)

FADE_WIDTH = 5
FADE_WIDTH_AMBER = 6
MINUTES_PER_PAD = 1
RECONNECT_INTERVAL = 2


class LaunchpadConnection:
    """Wraps a Launchpad device and reconnects transparently on failure."""

    def __init__(self):
        self._lp = None
        self._last_check = 0.0

    def connect(self):
        launchpads = find_launchpads()
        if not launchpads:
            return False
        self._lp = launchpads[0]
        self._lp.open()
        self._lp.mode = Mode.PROG
        print("Launchpad connected.")
        return True

    def is_healthy(self) -> bool:
        if not self._lp:
            return False
        try:
            self._lp.device_inquiry()
            return True
        except Exception:
            return False

    def ensure_connected(self):
        now = time.monotonic()
        if now - self._last_check < RECONNECT_INTERVAL:
            return
        self._last_check = now

        if self.is_healthy():
            return

        print("Launchpad disconnected. Waiting for reconnect...")
        self.close()
        self._lp = None
        while True:
            try:
                if self.connect():
                    return
            except Exception:
                pass
            time.sleep(RECONNECT_INTERVAL)

    @property
    def grid(self):
        return self._lp.grid

    def poll_for_event(self, **kwargs):
        return self._lp.poll_for_event(**kwargs)

    def close(self):
        if self._lp:
            try:
                self._lp.close()
            except Exception:
                pass


@contextmanager
def launchpad_session():
    lp = LaunchpadConnection()
    if not lp.connect():
        print("No Launchpad Mini MK3 found. Is it connected via USB?")
        sys.exit(1)
    try:
        yield lp
    finally:
        try:
            for led in lp.grid.led_range():
                del led.color
        except Exception:
            pass
        lp.close()


def led_order() -> list[tuple[int, int]]:
    return [(row, col) for col in range(GRID_SIZE) for row in range(GRID_SIZE)]


def update_grid(lp, fraction: float, order: list[tuple[int, int]]):
    if isinstance(lp, LaunchpadConnection):
        lp.ensure_connected()

    is_amber = 0.25 < fraction <= 0.60
    fade = FADE_WIDTH_AMBER if is_amber else FADE_WIDTH
    lit_float = fraction * TOTAL_LEDS
    for i, (row, col) in enumerate(order):
        brightness = (lit_float - i) / fade
        rgb = color_for_led(fraction, brightness)
        led = lp.grid.led(row, col)
        if rgb is not None:
            led.color = rgb
        else:
            try:
                del led.color
            except AttributeError:
                pass


def pad_index_in_order(button_name: str, order: list[tuple[int, int]]) -> int | None:
    row, col = (int(x) for x in button_name.split("x"))
    for i, (r, c) in enumerate(order):
        if r == row and c == col:
            return i + 1
    return None


def wait_for_pad_selection(lp, order: list[tuple[int, int]]) -> int:
    brightness = time_of_day_brightness()
    for i, (row, col) in enumerate(order):
        r, g, b = selection_color_for_minute(i)
        lp.grid.led(row, col).color = rgb_to_hex(
            _dim(r, brightness), _dim(g, brightness), _dim(b, brightness)
        )

    print("Press a pad to set the timer (each pad = 1 min, max 64 min)")

    while True:
        event = lp.poll_for_event(timeout=60)
        if event is None:
            continue
        button_event = ButtonEvent(event, list(lp.grid.led_range()))
        if button_event.type != ButtonEvent.PRESS or button_event.button is None:
            continue
        index = pad_index_in_order(button_event.button.name, order)
        if index is not None:
            return index * MINUTES_PER_PAD * 60
