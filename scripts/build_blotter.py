"""Raw KCEX exports  ->  private blotter + public monthly aggregate + figures.

Anything under private/ may carry per-trade detail. Anything under data/ and
figures/ is aggregate only and is safe to commit.

    python3 scripts/build_blotter.py [--starting-capital 12345]
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import metrics  # noqa: E402
from src.kcex import cross_check, load_fills  # noqa: E402
from src.realized import daily_net, fees_by_period, realized_events  # noqa: E402
from src.roundtrip import build_round_trips  # noqa: E402
from src.schema import AnnotatedTrade  # noqa: E402
from src.sources import EXPORT_2025_11, EXPORT_2026_05  # noqa: E402

PRIVATE = ROOT / "private" / "derived"
PUBLIC = ROOT / "data"
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("blotter")


def main(starting_capital: float | None) -> None:
    PRIVATE.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)

    # The wider export is the single source of truth; the narrower one is a check.
    base = load_fills(EXPORT_2026_05)
    check = load_fills(EXPORT_2025_11)
    in_window, matched, unmatched = cross_check(base, check)

    events = realized_events(base)
    fees_m = fees_by_period(base)
    daily = daily_net(base)
    trips, warns = build_round_trips(base)

    total_fees = float(sum(f.fee_usdt for f in base))
    s = metrics.summarize_realized(events, total_fees)
    cum = metrics.cumulative_daily(daily)
    dd = metrics.max_drawdown(cum)
    eq = metrics.equity_curve(daily, starting_capital)

    # ---- private: full per-close blotter, ready for risk annotation --------
    with (PRIVATE / "realized_events.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["closed_at_utc", "symbol", "side", "qty", "exit_price",
                    "gross_pnl_usdt", "exit_fee_usdt", "notional_usdt", "role",
                    "planned_risk_usdt", "strategy_tag", "rule_violation", "note"])
        for e in events:
            w.writerow([f"{e.ts:%Y-%m-%d %H:%M:%S}", e.symbol, e.side.value, e.qty,
                        e.price, round(e.gross_pnl_usdt, 4), round(e.exit_fee_usdt, 4),
                        round(e.notional_usdt, 2), "maker" if e.maker else "taker",
                        "", "", "", ""])

    with (PRIVATE / "daily_net.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date_utc", "net_usdt", "cumulative_net_usdt"])
        for (d, v), (_, c) in zip(daily, cum):
            w.writerow([d, round(v, 2), round(c, 2)])

    (PRIVATE / "reconciliation.txt").write_text(
        "TIMEZONE (measured against BTCUSDT 1m candles, see scripts/verify_timezone.py)\n"
        f"  {EXPORT_2025_11.label}: stamps are UTC+{EXPORT_2025_11.tz_offset_hours}\n"
        f"  {EXPORT_2026_05.label}: stamps are UTC+{EXPORT_2026_05.tz_offset_hours}\n"
        "  The two exports of the same account differ by 3h on every overlapping row.\n\n"
        "CROSS-CHECK of the narrow export against the wide one, after UTC normalisation\n"
        f"  rows in the overlapping window: {in_window}\n"
        f"  matched: {matched}\n"
        f"  unmatched: {unmatched}\n\n"
        f"ROUND-TRIP RECONSTRUCTION: {len(trips)} trips, {len(warns)} warnings\n"
        "  Round trips are approximate. Residual positions never return to flat,\n"
        "  so the realized-event series (one row per closing fill) is authoritative.\n\n"
        + "\n".join(warns) + "\n"
    )

    # ---- public: aggregate only -------------------------------------------
    monthly: dict[str, dict[str, float]] = {}
    for e in events:
        m = monthly.setdefault(f"{e.ts:%Y-%m}",
                               {"closes": 0, "wins": 0, "gross": 0.0})
        m["closes"] += 1
        m["wins"] += 1 if e.gross_pnl_usdt > 0 else 0
        m["gross"] += float(e.gross_pnl_usdt)

    with (PUBLIC / "public_monthly_stats.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["month_utc", "closes", "wins", "win_rate",
                    "gross_pnl_usdt", "all_fees_usdt", "net_pnl_usdt"])
        for m in sorted(monthly):
            v = monthly[m]
            f_ = float(fees_m.get(m, 0))
            w.writerow([m, int(v["closes"]), int(v["wins"]),
                        round(v["wins"] / v["closes"], 4),
                        round(v["gross"], 2), round(f_, 2), round(v["gross"] - f_, 2)])

    # ---- console -----------------------------------------------------------
    print("\n" + "=" * 72)
    print(f"WINDOW          {s.first} .. {s.last}   (UTC)")
    print(f"closing fills   {s.n_closes}     long {s.n_long} / short {s.n_short}"
          f"     maker {s.maker_share:.0%}")
    print(f"gross realized  {s.gross_usdt:>12,.2f} USDT")
    print(f"all fees        {s.fees_usdt:>12,.2f} USDT   = {s.cost_drag:.1%} of gross profit")
    print(f"NET             {s.net_usdt:>12,.2f} USDT")
    print(f"win rate        {s.win_rate:.1%}     profit factor {s.profit_factor:.2f}"
          f"     payoff {s.payoff_ratio:.2f}")
    print(f"avg win/loss    {s.avg_win_usdt:,.2f} / {s.avg_loss_usdt:,.2f}")
    print(f"best / worst    {s.largest_win_usdt:,.2f} / {s.largest_loss_usdt:,.2f}")
    print(f"tail p05 / p95  {s.p05_usdt:,.2f} / {s.p95_usdt:,.2f}")
    print(f"notional med    {s.median_notional_usdt:,.0f} USDT   max {s.max_notional_usdt:,.0f}")
    print(f"max DD (USDT)   {dd.max_dd_usdt:>12,.2f}   peak {dd.peak_at} -> trough "
          f"{dd.trough_at}   recovered {dd.recovered_at or 'NOT in window'}")
    if eq:
        print(f"equity index    start 100 -> end {eq[-1][1]:.1f}"
              f"   (starting capital {starting_capital:,.0f} USDT)")
    else:
        print("equity index    UNAVAILABLE: pass --starting-capital, and confirm no "
              "deposits/withdrawals in window")
    print("=" * 72)
    print(f"\nprivate/derived/realized_events.csv  {len(events)} rows")
    print(f"private/derived/daily_net.csv        {len(daily)} days")
    print(f"private/derived/reconciliation.txt   cross-check {matched}/{in_window} matched, "
          f"{unmatched} unmatched")
    print(f"data/public_monthly_stats.csv        {len(monthly)} months")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--starting-capital", type=float, default=None)
    a = ap.parse_args()
    main(a.starting_capital)
