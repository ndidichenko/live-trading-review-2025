"""Emit live_book_2025.json for the ai-quant-workflow webapp.

The review repo holds the private sources; the webapp is a private research app
that already holds proprietary edge material, so sleeve names are kept real here.
Nothing this writes is committed to the public review repo.

    python3 scripts/export_webapp_json.py [OUT_DIR]

Default OUT_DIR is the ai-quant-workflow webapp's public/ directory.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import metrics  # noqa: E402
from src.blotter import load_sheet  # noqa: E402
from src.kcex import load_fills  # noqa: E402
from src.realized import daily_net, realized_events  # noqa: E402
from src.schema import Side  # noqa: E402
from src.sources import EXPORT_2026_05  # noqa: E402

CAPITAL = 15_000.0
DEFAULT_OUT = (ROOT.parent / "ai-quant-workflow" / ".claude" / "worktrees"
               / "live-book-page" / "webapp" / "public")
BTC_CSV = ROOT / "private" / "derived" / "btc_daily.csv"


def main(out_dir: Path) -> None:
    fills = load_fills(EXPORT_2026_05)
    ev = realized_events(fills)
    daily = daily_net(fills)
    sheet, rep = load_sheet(ROOT / "private" / "raw" / "LiveTrading_2025_Latest.xlsx",
                            "Live 2025")

    gross = sum(float(e.gross_pnl_usdt) for e in ev)
    fees = float(sum(f.fee_usdt for f in fills))
    net = gross - fees

    eq = metrics.equity_curve(daily, CAPITAL)
    import csv as _csv
    btc = {}
    with BTC_CSV.open() as fh:
        for row in _csv.DictReader(fh):
            btc[row["date_utc"]] = float(row["close_usdt"])
    lo, hi = f"{eq[0][0]}", f"{eq[-1][0]}"
    bdays = sorted(d for d in btc if lo <= d <= hi)
    b0 = btc[bdays[0]]
    bench = {d: btc[d] / b0 * 100 for d in bdays}

    curve, last_b = [], 100.0
    for d, v in eq:
        last_b = bench.get(f"{d}", last_b)
        curve.append({"date": f"{d}", "book": round(v, 2), "btc": round(last_b, 2)})

    peak, uw = -1e18, []
    for d, v in eq:
        peak = max(peak, v)
        uw.append({"date": f"{d}", "dd": round((v / peak - 1) * 100, 2)})
    trough = min(uw, key=lambda x: x["dd"])

    r = sheet["R+/-"].dropna()
    monthly = sheet.groupby(sheet["entry"].dt.to_period("M")).agg(
        r=("R+/-", "sum"), n=("R+/-", "size"), w=("R+/-", lambda x: (x > 0).sum()))
    months = [{"month": str(m), "r": round(float(v["r"]), 2), "trades": int(v["n"]),
               "wins": int(v["w"]),
               "win_rate": round(float(v["w"]) / float(v["n"]), 3)}
              for m, v in monthly.iterrows()]

    # R histogram, quarter-R buckets
    hist = defaultdict(int)
    for x in r:
        hist[round(float(x) * 4) / 4] += 1
    rhist = [{"bin": k, "count": v} for k, v in sorted(hist.items())]

    sleeves = []
    for name, g in sheet.groupby(sheet["sleeve_raw"]):
        if name in ("nan", ""):
            continue
        rr = g["R+/-"].dropna()
        sleeves.append({
            "name": name, "trades": int(len(g)), "r": round(float(rr.sum()), 2),
            "usd": round(float(g["net_usd"].sum()), 0),
            "win_rate": round(float((rr > 0).mean()), 3) if len(rr) else None,
            "first": f"{g['entry'].min():%Y-%m-%d}", "last": f"{g['entry'].max():%Y-%m-%d}",
        })
    sleeves.sort(key=lambda s: -s["r"])

    dd_days = sorted(daily, key=lambda x: -x[1])
    top_days = [{"date": f"{d}", "usd": round(v, 0),
                 "share_of_net": round(v / net * 100, 1)} for d, v in dd_days[:6]]

    ladder, mx = [], 0.0
    for _, row in sheet.sort_values("entry").iterrows():
        v = float(row["RISK"]) if row["RISK"] == row["RISK"] else 0
        if v > mx:
            ladder.append({"risk": v, "date": f"{row['entry']:%Y-%m-%d}",
                           "step": round(v / mx, 2) if mx else None})
            mx = v

    longs = sum(float(e.gross_pnl_usdt) for e in ev if e.side is Side.LONG)
    shorts = sum(float(e.gross_pnl_usdt) for e in ev if e.side is Side.SHORT)

    payload = {
        "meta": {
            "generated": f"{date.today()}",
            "generator": "live-trading-review-2025/scripts/export_webapp_json.py",
            "public_repo": "https://github.com/ndidichenko/live-trading-review-2025",
            "documented_window": "2025-03-09..2025-12-30",
            "venue_window": "2025-06-02..2025-12-30",
            "capital_usdt": CAPITAL,
            "venue": "KCEX", "instrument": "BTC/USDT perp",
            "benchmark": "Binance BTCUSDT spot daily close",
            "date_repair": {
                "entry_transposed": rep.entry_transposed,
                "exit_transposed": rep.exit_transposed,
                "exit_before_entry_fixed":
                    rep.exit_before_entry_before - rep.exit_before_entry_after,
            },
        },
        "headline": {
            "trades": int(len(sheet)), "closing_fills": len(ev),
            "total_r": round(float(r.sum()), 2),
            "venue_r": round(float(sheet[sheet["entry"] >= "2025-06-01"]["R+/-"].sum()), 2),
            "ramp_r": round(float(sheet[sheet["entry"] < "2025-06-01"]["R+/-"].sum()), 2),
            "gross_usdt": round(gross, 2), "fees_usdt": round(fees, 2),
            "net_usdt": round(net, 2), "return_pct": round(net / CAPITAL * 100, 1),
            "btc_pct": round(bench[bdays[-1]] - 100, 1),
            "max_dd_pct": trough["dd"], "max_dd_date": trough["date"],
            "win_rate": round(float((r > 0).mean()), 3),
            "payoff": round(float(r[r > 0].mean() / abs(r[r < 0].mean())), 2),
            "long_usdt": round(longs, 0), "short_usdt": round(shorts, 0),
            "best_r": round(float(r.max()), 2), "worst_r": round(float(r.min()), 2),
        },
        "curve": curve, "underwater": uw, "monthly": months, "rhist": rhist,
        "sleeves": sleeves, "top_days": top_days, "ladder": ladder,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "live_book_2025.json"
    out.write_text(json.dumps(payload, indent=1))
    print(f"{out}  {out.stat().st_size/1024:.0f} KB")
    print(f"  {payload['headline']['trades']} trades, {payload['headline']['total_r']:+}R, "
          f"{payload['headline']['net_usdt']:+,.0f} USDT, {len(sleeves)} sleeves")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT)
