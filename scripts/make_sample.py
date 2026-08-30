"""Generate data/sample_synthetic.csv so the repo runs without private data.

Deliberately synthetic. It reproduces the column shape and roughly the win rate
and payoff of the real book, and nothing else: timings are uniform, prices are a
random walk, and no real trade influences any row. Nobody can recover a rule
from it, which is the point.
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_synthetic.csv"
N, WIN_RATE, SEED = 60, 0.31, 20251010


def main() -> None:
    rng = random.Random(SEED)
    t = datetime(2025, 6, 2, tzinfo=timezone.utc)
    px = 100_000.0
    rows = []
    for _ in range(N):
        t += timedelta(hours=rng.uniform(4, 60))
        px *= 1 + rng.gauss(0, 0.02)
        side = rng.choice(["long", "short"])
        qty = round(rng.uniform(0.05, 1.2), 4)
        win = rng.random() < WIN_RATE
        pnl = rng.gauss(400, 260) if win else -abs(rng.gauss(150, 90))
        fee = round(qty * px * 0.0002, 4)
        rows.append({
            "closed_at_utc": t.strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": "BTCUSDT", "side": side, "qty": qty,
            "exit_price": round(px, 1), "gross_pnl_usdt": round(pnl, 2),
            "exit_fee_usdt": fee, "notional_usdt": round(qty * px, 2),
            "role": rng.choice(["maker", "taker"]),
            "planned_risk_usdt": 150, "strategy_tag": rng.choice("ABC"),
            "rule_violation": "", "note": "",
        })

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{OUT}  {len(rows)} SYNTHETIC rows")


if __name__ == "__main__":
    main()
