"""Re-derive each export's timezone from price, rather than trusting a label.

For a set of taker fills, compare the recorded fill price against the BTCUSDT
1-minute close at each candidate UTC offset. The correct offset is the one where
the fill price sits on the candle; a wrong offset moves BTC by far more than the
tick noise.

    python3 scripts/verify_timezone.py            # scan both configured exports
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import random
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.sources import ALL  # noqa: E402

KLINE = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&startTime=%d&limit=1"
NEAR_PCT = 0.15
_cache: dict[int, float | None] = {}


def close_at(ms: int) -> float | None:
    if ms not in _cache:
        _cache[ms] = None
        for _ in range(4):
            try:
                with urllib.request.urlopen(KLINE % ms, timeout=20) as resp:
                    k = json.load(resp)
                _cache[ms] = float(k[0][4]) if k else None
                break
            except Exception:  # network hiccup: retry, then give up on this minute
                time.sleep(1.2)
    return _cache[ms]


def scan(src, offsets=range(0, 6), n=30) -> None:
    rows = [
        r for r in csv.DictReader(open(src.path, encoding="utf-8-sig"))
        if r["Futures"] == "BTC USDT" and r.get("Role") == "Taker"
    ]
    random.seed(3)
    sample = random.sample(rows, min(n, len(rows)))
    print(f"\n{src.label}  (taker fills, n={len(sample)})  configured: UTC+{src.tz_offset_hours}")
    for off in offsets:
        devs = []
        for r in sample:
            naive = dt.datetime.strptime(r["Time"], "%Y-%m-%d %H:%M:%S")
            utc = (naive - dt.timedelta(hours=off)).replace(tzinfo=dt.timezone.utc)
            c = close_at(int(utc.timestamp() // 60 * 60 * 1000))
            if c:
                devs.append(abs(float(r["Order Price"]) - c) / c * 100)
            time.sleep(0.06)
        if devs:
            near = sum(x < NEAR_PCT for x in devs) / len(devs)
            mark = "  <== best" if near > 0.5 else ""
            print(f"   UTC+{off}: median |dev| {statistics.median(devs):6.3f}%   "
                  f"within {NEAR_PCT}%: {near:4.0%}{mark}")


if __name__ == "__main__":
    for s in ALL:
        scan(s)
