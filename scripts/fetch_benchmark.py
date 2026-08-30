"""Cache BTCUSDT daily closes so the benchmark in every figure is reproducible.

Writes private/derived/btc_daily.csv. The benchmark is stated, sourced and dated
rather than quoted from memory: a headline that beats "BTC" means nothing until
the reader can see which series, which window, and which day it closed on.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "private" / "derived" / "btc_daily.csv"
URL = ("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d"
       "&startTime=%d&endTime=%d&limit=1000")


def fetch(start: str, end: str) -> list[tuple[str, float]]:
    to_ms = lambda s: int(dt.datetime.strptime(s, "%Y-%m-%d")
                          .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    with urllib.request.urlopen(URL % (to_ms(start), to_ms(end)), timeout=30) as r:
        rows = json.load(r)
    return [(dt.datetime.fromtimestamp(k[0] / 1000, dt.timezone.utc).strftime("%Y-%m-%d"),
             float(k[4])) for k in rows]


if __name__ == "__main__":
    a = sys.argv[1:]
    start, end = (a + ["2024-12-31", "2026-01-02"])[:2]
    rows = fetch(start, end)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date_utc", "close_usdt"])
        w.writerows(rows)
    first, last = rows[0], rows[-1]
    print(f"{OUT}  {len(rows)} days  {first[0]} {first[1]:,.0f} -> {last[0]} {last[1]:,.0f}"
          f"  ({(last[1]/first[1]-1)*100:+.2f}%)   source: Binance BTCUSDT spot 1d close")
