import json
import os
import tempfile
import threading
import time
from datetime import datetime, date, time as dtime
from typing import cast

import pytz
import yfinance as yf  # pyright: ignore[reportMissingTypeStubs]
from typing import TypedDict

# Constants

SYMBOL = "NVDA"
STATE_FILE = "/opt/nvda_ticker/state.json"
ET = pytz.timezone("America/New_York")
MARKET_OPEN = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)

# Shared state

_lock = threading.Lock()
_ticker = yf.Ticker(SYMBOL)


class TickerState(TypedDict):
    date: str
    open_price: float | None
    min_price: float | None
    max_price: float | None
    last_price: float | None
    eod_reported: bool


state: TickerState = {
    "date": "",
    "open_price": None,
    "min_price": None,
    "max_price": None,
    "last_price": None,
    "eod_reported": False,
}

# State helpers


def _default_state() -> TickerState:
    return {
        "date": date.today().isoformat(),
        "open_price": None,
        "min_price": None,
        "max_price": None,
        "last_price": None,
        "eod_reported": False,
    }


def load_state() -> None:
    global state
    today = date.today().isoformat()
    try:
        with open(STATE_FILE) as f:
            saved: TickerState = cast(TickerState, json.load(f))
        if saved.get("date") == today:
            state = saved
            return
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    state = _default_state()


def save_state() -> None:
    dir_ = os.path.dirname(STATE_FILE)
    fd, tmp = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f)
        os.replace(tmp, STATE_FILE)
    except Exception:
        os.unlink(tmp)
        raise


# Market helpers


def get_price() -> float:
    last_price = _ticker.fast_info.last_price  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if last_price is None:
        raise ValueError("No price data available")
    elif not isinstance(last_price, (int, float)):
        raise ValueError(f"Unexpected price type: {type(last_price)}")  # pyright: ignore[reportUnknownArgumentType]
    return float(last_price)


def now_et() -> datetime:
    return datetime.now(ET)


def is_market_open(t: datetime) -> bool:
    if t.weekday() >= 5:
        return False
    current = t.time().replace(second=0, microsecond=0)
    return MARKET_OPEN <= current < MARKET_CLOSE


def fmt_sign(n: float) -> str:
    return "+" if n >= 0 else ""


# Threads


def ticker_loop() -> None:
    while True:
        t = now_et()
        if is_market_open(t):
            try:
                price = get_price()

                with _lock:
                    last = state["last_price"]
                    delta = price - last if last is not None else 0.0

                    if state["open_price"] is None:
                        state["open_price"] = price
                    state["min_price"] = min(state["min_price"] or price, price)
                    state["max_price"] = max(state["max_price"] or price, price)
                    state["last_price"] = price
                    save_state()

                sign = fmt_sign(delta)
                ts = t.strftime("%Y-%m-%d %H:%M:%S")
                print(
                    f"[{ts} ET] {SYMBOL}: ${price:.2f}  ({sign}{delta:.2f})", flush=True
                )

            except Exception as e:
                print(f"Error fetching price: {e}", flush=True)

        time.sleep(60)


def print_eod_summary() -> None:
    with _lock:
        open_p = state["open_price"]
        close_p = state["last_price"]
        low_p = state["min_price"]
        high_p = state["max_price"]
        today = state["date"]

    if open_p is None or close_p is None or low_p is None or high_p is None:
        print(f"=== {SYMBOL} End of Day [{today}] — no data collected ===", flush=True)
        return

    change = close_p - open_p
    pct = (change / open_p) * 100
    sign = fmt_sign(change)

    print(f"\n=== {SYMBOL} End of Day [{today}] ===", flush=True)
    print(f"  Open:   ${open_p:.2f}", flush=True)
    print(f"  Close:  ${close_p:.2f}", flush=True)
    print(f"  Low:    ${low_p:.2f}", flush=True)
    print(f"  High:   ${high_p:.2f}", flush=True)
    print(f"  Change: {sign}${change:.2f} ({sign}{pct:.2f}%)\n", flush=True)


def eod_loop() -> None:
    t = now_et()
    target = t.replace(hour=16, minute=0, second=0, microsecond=0)
    wait = (target - t).total_seconds()
    if wait > 0:
        time.sleep(wait)

    with _lock:
        already_reported = state["eod_reported"]

    if not already_reported:
        print_eod_summary()
        with _lock:
            state["eod_reported"] = True
            save_state()


# Entry point


def main() -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    load_state()

    t1 = threading.Thread(target=ticker_loop, name="ticker", daemon=True)
    t2 = threading.Thread(target=eod_loop, name="eod", daemon=True)
    t1.start()
    t2.start()
    t1.join()


if __name__ == "__main__":
    main()
