import argparse
import signal
import sys
import threading
import time

from launchprogress.duration import format_time, parse_duration
from launchprogress.grid import (
    LaunchpadConnection,
    launchpad_session,
    led_order,
    update_grid,
    wait_for_pad_selection,
)

IDLE_COLOR = "#1a1a1a"
COMPLETE_COLOR = "#1a0000"

order = led_order()


def _ensure(lp):
    if isinstance(lp, LaunchpadConnection):
        lp.ensure_connected()


def clear_leds(lp):
    _ensure(lp)
    for led in lp.grid.led_range():
        try:
            del led.color
        except AttributeError:
            pass


def show_idle(lp):
    _ensure(lp)
    clear_leds(lp)
    lp.grid.led(0, 0).color = IDLE_COLOR


def show_complete(lp):
    _ensure(lp)
    for led in lp.grid.led_range():
        led.color = COMPLETE_COLOR


def run_timer(lp, total_seconds: float, cancel_check=None):
    update_grid(lp, 1.0, order)
    print(f"Remaining: {format_time(total_seconds)}", end="", flush=True)

    start = time.monotonic()

    while (remaining := total_seconds - (time.monotonic() - start)) > 0:
        if cancel_check and cancel_check():
            return False
        fraction = remaining / total_seconds
        update_grid(lp, fraction, order)
        print(f"\rRemaining: {format_time(remaining)}   ", end="", flush=True)
        time.sleep(0.1)

    print("\rTimer complete!")
    play_completion(lp, cancel_check)
    return True


def play_completion(lp, cancel_check=None):
    end_time = time.monotonic() + 5

    while time.monotonic() < end_time:
        if cancel_check and cancel_check():
            return
        cycle_start = time.monotonic()
        while (elapsed := time.monotonic() - cycle_start) < 1.0:
            if cancel_check and cancel_check():
                return
            if elapsed < 0.5:
                fraction = 1.0 - elapsed / 0.5
            else:
                fraction = (elapsed - 0.5) / 0.5
            update_grid(lp, fraction, order)
            time.sleep(0.05)


# --- Server mode ---


class TimerState:
    def __init__(self):
        self.lock = threading.Lock()
        self._running = False
        self._cancel = False
        self._completed = False
        self.total_seconds = 0.0
        self.start_time = 0.0
        self.thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        with self.lock:
            return self._running

    @running.setter
    def running(self, value: bool):
        with self.lock:
            self._running = value

    @property
    def cancel(self) -> bool:
        with self.lock:
            return self._cancel

    @cancel.setter
    def cancel(self, value: bool):
        with self.lock:
            self._cancel = value

    @property
    def remaining(self) -> float:
        with self.lock:
            if not self._running:
                return 0.0
            return max(0.0, self.total_seconds - (time.monotonic() - self.start_time))


def create_app(lp):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    state = TimerState()

    def server_timer_loop(total_seconds: float):
        state.start_time = time.monotonic()
        completed = run_timer(lp, total_seconds, cancel_check=lambda: state.cancel)

        if completed:
            show_complete(lp)
        else:
            show_idle(lp)

        with state.lock:
            state._running = False
            state._cancel = False
            state._completed = completed

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        show_idle(lp)
        yield
        clear_leds(lp)

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.timer = state

    class TimerRequest(BaseModel):
        minutes: float

    @app.post("/timer")
    def start_timer(req: TimerRequest):
        with state.lock:
            if state._running:
                raise HTTPException(409, "Timer already running")
            if req.minutes <= 0:
                raise HTTPException(400, "Minutes must be positive")
            state._running = True
            state._cancel = False
            state._completed = False
            state.total_seconds = req.minutes * 60

        state.thread = threading.Thread(
            target=server_timer_loop, args=(state.total_seconds,), daemon=True
        )
        state.thread.start()

        return {
            "status": "started",
            "minutes": req.minutes,
            "display": format_time(state.total_seconds),
        }

    @app.get("/timer")
    def get_timer():
        with state.lock:
            if not state._running:
                return {"running": False, "completed": state._completed}
            remaining = max(
                0.0, state.total_seconds - (time.monotonic() - state.start_time)
            )
        return {
            "running": True,
            "remaining_seconds": round(remaining, 1),
            "display": format_time(remaining),
        }

    @app.delete("/timer")
    def cancel_timer():
        with state.lock:
            if state._running:
                state._cancel = True
            elif not state._completed:
                raise HTTPException(404, "No timer running")
            else:
                state._completed = False
                show_idle(lp)
                return {"status": "dismissed"}

        if state.thread:
            state.thread.join(timeout=3)
        return {"status": "cancelled"}

    return app


def run_server(lp, port: int = 8000):
    import uvicorn

    app = create_app(lp)
    uvicorn.run(app, host="0.0.0.0", port=port)


# --- CLI ---


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launchpad Mini MK3 countdown timer")
    parser.add_argument(
        "duration",
        nargs="?",
        help="e.g. 30s, 5m, 1h30m. Omit to select via pad.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the API server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    with launchpad_session() as lp:

        def cleanup(signum=None, frame=None):
            print("\nCancelled.")
            clear_leds(lp)
            lp.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)

        if args.serve:
            run_server(lp, port=args.port)
        elif args.duration:
            total_seconds = parse_duration(args.duration)
            print(f"Timer: {format_time(total_seconds)}")
            run_timer(lp, total_seconds)
        else:
            total_seconds = wait_for_pad_selection(lp, order)
            print(f"Timer: {format_time(total_seconds)}")
            run_timer(lp, total_seconds)


if __name__ == "__main__":
    main()
