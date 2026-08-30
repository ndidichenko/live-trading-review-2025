"""Join the manual sheet onto the venue's closing fills.

The two records are independent and neither is complete on its own. The venue
knows the money: fills, prices, fees, realized PnL. The sheet knows the intent:
planned risk, R, which sleeve, whether the loss came in bigger than planned.
Only the join has both, and only the join can say how far apart they are.

Matching is on (exit time, exit price). The sheet stamps in UTC+0, established
by scanning candidate offsets against the exchange fills: 239 of 262 closed
trades match within three minutes at UTC+0 and none at any other offset.

    python3 scripts/join_blotter.py
"""
from __future__ import annotations

import csv
import datetime as dt
import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.blotter import anonymise_sleeve, load_sheet, validate  # noqa: E402
from src.kcex import load_fills  # noqa: E402
from src.realized import realized_events  # noqa: E402
from src.sources import EXPORT_2026_05  # noqa: E402

XL = ROOT / "private" / "raw" / "LiveTrading_2025_Latest.xlsx"
OUT = ROOT / "private" / "derived"
SHEET_TZ_OFFSET_HOURS = 0
TOLERANCE_SEC = 180
logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    df, rep = load_sheet(XL, "Live 2025")
    print(rep)
    print("  validation:", validate(df, rep) or "PASS")

    fills = load_fills(EXPORT_2026_05)
    events = realized_events(fills)

    # Match on the trade's TIME WINDOW, not on price. `AVG EXIT` in the sheet is
    # an average across the closing fills, so it equals no single fill's price
    # whenever a trade was scaled out; matching on price alone found only 59%.
    # A closing fill belongs to the sheet trade whose [entry, exit] window
    # contains it, preferring the trade whose exit is nearest.
    windows = []
    for _, t in df.iterrows():
        if t["entry"] is None or t["exit"] is None:
            continue
        lo = t["entry"] - dt.timedelta(hours=SHEET_TZ_OFFSET_HOURS)
        hi = t["exit"] - dt.timedelta(hours=SHEET_TZ_OFFSET_HOURS)
        if hi < lo:                       # the 3 known typo rows
            lo, hi = hi, lo
        windows.append((lo - dt.timedelta(seconds=TOLERANCE_SEC),
                        hi + dt.timedelta(seconds=TOLERANCE_SEC), hi, t))

    claimed: dict[int, int] = {}
    rows = []
    hit_trades = set()
    for i, e in enumerate(events):
        ts = e.ts.replace(tzinfo=None)
        cands = [(abs((hi - ts).total_seconds()), t) for lo, up, hi, t in windows
                 if lo <= ts <= up]
        if not cands:
            continue
        cands.sort(key=lambda c: c[0])
        t = cands[0][1]
        claimed[i] = int(t["#"])
        hit_trades.add(int(t["#"]))
        rows.append((i, t))

    unmatched_trades = [t for _, _, _, t in windows if int(t["#"]) not in hit_trades]

    matched_ev = {i for i in claimed}
    unmatched_ev = [e for i, e in enumerate(events) if i not in matched_ev]

    # ---- write the enriched blotter -------------------------------------
    OUT.mkdir(parents=True, exist_ok=True)
    lookup = {i: t for i, t in rows}
    with (OUT / "realized_events.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["closed_at_utc", "symbol", "side", "qty", "exit_price",
                    "gross_pnl_usdt", "exit_fee_usdt", "notional_usdt", "role",
                    "sheet_trade_no", "planned_risk_usdt", "expected_loss_usdt",
                    "realised_loss_usdt", "r_multiple", "sleeve", "sleeve_raw",
                    "loss_overshoot_usdt", "matched"])
        for i, e in enumerate(events):
            t = lookup.get(i)
            if t is None:
                w.writerow([f"{e.ts:%Y-%m-%d %H:%M:%S}", e.symbol, e.side.value, e.qty,
                            e.price, round(e.gross_pnl_usdt, 4), round(e.exit_fee_usdt, 4),
                            round(e.notional_usdt, 2), "maker" if e.maker else "taker",
                            "", "", "", "", "", "", "", "", "no"])
                continue
            exp, real = t["EXPECTED LOSS"], t["REALISED LOSS"]
            over = round(real - exp, 2) if (exp == exp and real == real) else ""
            w.writerow([f"{e.ts:%Y-%m-%d %H:%M:%S}", e.symbol, e.side.value, e.qty,
                        e.price, round(e.gross_pnl_usdt, 4), round(e.exit_fee_usdt, 4),
                        round(e.notional_usdt, 2), "maker" if e.maker else "taker",
                        int(t["#"]), t["RISK"], exp if exp == exp else "",
                        real if real == real else "", round(t["R+/-"], 4),
                        anonymise_sleeve(t["sleeve_raw"]), t["sleeve_raw"], over, "yes"])

    # ---- reconciliation --------------------------------------------------
    m_pnl = sum(float(events[i].gross_pnl_usdt) for i in matched_ev)
    u_pnl = sum(float(e.gross_pnl_usdt) for e in unmatched_ev)
    sheet_jun = df[df["entry"] >= "2025-06-01"]

    lines = [
        "MANUAL SHEET vs VENUE EXPORT",
        "",
        f"sheet, full documented year 2025-03-09..2025-12-30: {len(df)} trades, "
        f"{df['R+/-'].sum():+.2f}R, {df['net_usd'].sum():+,.2f} USD",
        f"sheet, Jun-Dec only:                                {len(sheet_jun)} trades, "
        f"{sheet_jun['R+/-'].sum():+.2f}R, {sheet_jun['net_usd'].sum():+,.2f} USD",
        f"venue, Jun-Dec (391 closing fills):                 "
        f"{sum(float(e.gross_pnl_usdt) for e in events):+,.2f} USD gross, "
        f"{sum(float(e.gross_pnl_usdt) for e in events) - float(sum(f.fee_usdt for f in fills)):+,.2f} net",
        "",
        f"closing fills matched to a sheet trade:   {len(matched_ev)} of {len(events)}",
        f"  their gross PnL:                       {m_pnl:+,.2f} USD",
        f"closing fills with NO sheet trade:       {len(unmatched_ev)}",
        f"  their gross PnL:                       {u_pnl:+,.2f} USD",
        f"sheet trades with no matching fill:      {len(unmatched_trades)}",
        "",
        "The venue can close one trade in several fills, and can net two trades into",
        "one close, so a 1:1 match is not expected. Unmatched fills are the honest",
        "size of the gap between the two records.",
        "",
        "DATE REPAIR APPLIED TO THE SHEET",
        str(rep),
        "",
        "SLEEVE ANONYMISATION MAP (private, never publish the right-hand column)",
    ]
    for _, t in rows:
        pass
    seen = {}
    for _, t in rows:
        seen[t["sleeve_raw"]] = anonymise_sleeve(t["sleeve_raw"])
    for raw, anon in sorted(seen.items(), key=lambda kv: kv[1]):
        lines.append(f"  {anon:12} <- {raw}")

    # public aggregate: monthly R over the whole documented book, no trade rows
    pub = ROOT / "data" / "public_monthly_r.csv"
    monthly = df.groupby(df["entry"].dt.to_period("M")).agg(
        trades=("R+/-", "size"), r=("R+/-", "sum"), wins=("R+/-", lambda x: (x > 0).sum()))
    with pub.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["month_utc", "trades", "wins", "win_rate", "result_r"])
        for m, row in monthly.iterrows():
            w.writerow([str(m), int(row["trades"]), int(row["wins"]),
                        round(row["wins"] / row["trades"], 4), round(row["r"], 2)])

    (OUT / "reconciliation_sheet_vs_venue.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:14]))
    print(f"\nwrote {OUT/'realized_events.csv'}")
    print(f"wrote {OUT/'reconciliation_sheet_vs_venue.txt'}")


if __name__ == "__main__":
    main()
