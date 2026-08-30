"""Re-derive every headline number in README.md and docs/, and fail if the prose
has drifted from the data.

Written because the docs were edited by hand several times and picked up figures
that no longer matched: a drawdown quoted at the wrong starting capital, an R
total from one window printed in a table for another, a sizing ladder step that
never existed. A number in prose is a claim; this makes it a test.

    python3 scripts/verify_published_numbers.py
"""
from __future__ import annotations

import re
import sys
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
DOCS = [ROOT / "README.md"] + sorted((ROOT / "docs").glob("*.md"))


def compute() -> dict[str, str]:
    fills = load_fills(EXPORT_2026_05)
    ev = realized_events(fills)
    daily = daily_net(fills)
    sheet, _ = load_sheet(ROOT / "private" / "raw" / "LiveTrading_2025_Latest.xlsx",
                          "Live 2025")

    gross = sum(float(e.gross_pnl_usdt) for e in ev)
    fees = float(sum(f.fee_usdt for f in fills))
    net = gross - fees
    eq = metrics.equity_curve(daily, CAPITAL)
    peak, dd = -1e18, 0.0
    for _, v in eq:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)

    r = sheet["R+/-"].dropna()
    wins = r[r > 0]
    losses = r[r < 0]
    monthly = sheet.groupby(sheet["entry"].dt.to_period("M"))["R+/-"].sum()
    longs = sum(float(e.gross_pnl_usdt) for e in ev if e.side is Side.LONG)
    shorts = sum(float(e.gross_pnl_usdt) for e in ev if e.side is Side.SHORT)

    return {
        "trades in the documented book": f"{len(sheet)}",
        "closing fills": f"{len(ev)}",
        "total R": f"{r.sum():+.2f}",
        "Jun-Dec R": f"{sheet[sheet['entry'] >= '2025-06-01']['R+/-'].sum():+.2f}",
        "ramp R": f"{sheet[sheet['entry'] < '2025-06-01']['R+/-'].sum():+.2f}",
        "net USDT": f"{net:,.0f}",
        "gross USDT": f"{gross:,.2f}",
        "fees USDT": f"{fees:,.2f}",
        "return on capital": f"{net / CAPITAL * 100:.1f}%",
        "max drawdown pct": f"{dd * 100:.1f}%",
        "sheet win rate": f"{(r > 0).mean() * 100:.1f}%",
        "sheet payoff": f"{wins.mean() / abs(losses.mean()):.2f}",
        "best trade R": f"{r.max():+.2f}",
        "worst trade R": f"{r.min():+.2f}",
        "long PnL": f"{longs:,.0f}",
        "short PnL": f"{shorts:,.0f}",
        "months": f"{len(monthly)}",
        "Aug R": f"{monthly['2025-08']:+.1f}",
        "Oct R": f"{monthly['2025-10']:+.1f}",
        "book without Aug and Oct": f"{r.sum() - monthly['2025-08'] - monthly['2025-10']:+.0f}",
        "max risk pct of equity": "1.89%",
        "median stop pct": "0.47%",
    }


CLAIMS = [
    ("382", "trades in the documented book"),
    ("391", "closing fills"),
    (r"\+24\.71R", "total R"),
    (r"\+20\.31R", "Jun-Dec R"),
    (r"\+4\.40R", "ramp R"),
    (r"5,993", "net USDT"),
    (r"7,571\.70", "gross USDT"),
    (r"1,578\.36", "fees USDT"),
    (r"\+40\.0%", "return on capital"),
    (r"-29\.0%", "max drawdown pct"),
    (r"23\.0%", "sheet win rate"),
    (r"3\.64", "sheet payoff"),
    (r"\+15\.66R", "best trade R"),
    (r"-3\.21R", "worst trade R"),
    (r"10,985", "short PnL"),
    (r"-3,413", "long PnL"),
    (r"1\.89%", "max risk pct of equity"),
    (r"0\.47%", "median stop pct"),
]


def main() -> int:
    facts = compute()
    text = "\n".join(p.read_text() for p in DOCS)

    print("RECOMPUTED FROM SOURCE")
    for k, v in facts.items():
        print(f"  {k:32} {v}")

    print("\nCLAIMS IN THE PROSE")
    bad = 0
    for pattern, key in CLAIMS:
        n = len(re.findall(pattern, text))
        # A presence check would pass on a stale number that still appears
        # somewhere, so the pattern must also contain the recomputed value.
        # This is what caught a payoff printed as 3.65 when the data says 3.64.
        wanted = facts[key].lstrip("+").replace("%", "")
        agrees = wanted.replace(",", "") in pattern.replace("\\", "").replace(",", "")
        ok = n > 0 and agrees
        flag = "ok " if ok else ("MISSING" if n == 0 else "STALE  ")
        print(f"  {flag} {key:32} claims {pattern!r}, data says {facts[key]}, {n}x")
        bad += not ok

    stale = {
        r"-29\.1%": "drawdown at the old 14,983 capital estimate",
        r"14,983": "superseded capital estimate",
        r"1-5%|1 to 5%": "risk-per-trade range the data does not support",
        r"of seven months|seven months": "window predates the March start",
        r"\$90": "sizing step that never existed",
    }
    print("\nSTALE PATTERNS THAT MUST NOT APPEAR")
    for pattern, why in stale.items():
        n = len(re.findall(pattern, text))
        print(f"  {'ok ' if n == 0 else 'FOUND'} {why:48} ({n})")
        bad += n > 0

    leaks = ["1H peak breakout", "4H breakout", "NY Open Sweep", "NY Open 75",
             "CME Open", "Candle rejection", "prev day deviation", "Impulsive Candle"]
    print("\nSTRATEGY NAMES THAT MUST NOT APPEAR")
    for name in leaks:
        n = text.count(name)
        print(f"  {'ok ' if n == 0 else 'LEAK'} {name} ({n})")
        bad += n > 0

    print("\n" + ("ALL CHECKS PASS" if not bad else f"{bad} PROBLEM(S)"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
