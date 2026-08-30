"""Render the public figures. Aggregate only: no per-trade row leaves this script.

    python3 scripts/make_figures.py --starting-capital 15000

Each figure is written twice, `<name>.png` and `<name>-dark.png`, so a README
can serve the right one per theme with <picture>. The dark steps come from the
same validated ramps as the light ones; they are not an automatic inversion.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import metrics  # noqa: E402
from src.kcex import load_fills  # noqa: E402
from src.realized import daily_net, realized_events  # noqa: E402
from src.blotter import load_sheet  # noqa: E402
from src.sources import EXPORT_2026_05  # noqa: E402

FIG = ROOT / "figures"
BTC_CSV = ROOT / "private" / "derived" / "btc_daily.csv"

# Validated categorical slots. Slot 1 is the book, slot 2 the benchmark, and the
# assignment never changes between figures: colour follows the entity.
THEME = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e",
                  grid="#e4e3df", book="#2a78d6", bench="#eb6834", zero="#a8a7a2"),
    "dark":  dict(surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7",
                  grid="#333331", book="#3987e5", bench="#d95926", zero="#6b6a66"),
}
PCT = FuncFormatter(lambda v, _: f"{v:,.0f}%")


def style(ax, t, *, title, ylabel, zero_line=True):
    ax.set_facecolor(t["surface"])
    ax.figure.patch.set_facecolor(t["surface"])
    ax.set_title(title, color=t["ink"], fontsize=13, fontweight="600", loc="left", pad=14)
    ax.set_ylabel(ylabel, color=t["ink2"], fontsize=10)
    ax.tick_params(colors=t["ink2"], labelsize=9, length=0)
    ax.grid(axis="y", color=t["grid"], linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    if zero_line:
        ax.axhline(0, color=t["zero"], linewidth=1.0, zorder=1)


def load_btc() -> dict[date, float]:
    if not BTC_CSV.exists():
        raise SystemExit("run scripts/fetch_benchmark.py first")
    with BTC_CSV.open() as fh:
        return {datetime.strptime(r["date_utc"], "%Y-%m-%d").date(): float(r["close_usdt"])
                for r in csv.DictReader(fh)}


def save(fig, name, mode):
    FIG.mkdir(exist_ok=True)
    out = FIG / (f"{name}.png" if mode == "light" else f"{name}-dark.png")
    fig.savefig(out, dpi=170, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ", out.relative_to(ROOT))


def build(mode, daily, events, capital, btc, r_multiples, monthly_r):
    t = THEME[mode]
    eq = metrics.equity_curve(daily, capital)
    days = [d for d, _ in eq]
    lo, hi = days[0], days[-1]

    # benchmark indexed to 100 on the book's first day, same window: a benchmark
    # measured over a different window is not a benchmark.
    bdays = sorted(d for d in btc if lo <= d <= hi)
    base = btc[bdays[0]]
    bench = [(d, btc[d] / base * 100) for d in bdays]

    # 1 --- equity vs benchmark -------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(days, [v for _, v in eq], color=t["book"], linewidth=2, zorder=3)
    ax.plot([d for d, _ in bench], [v for _, v in bench],
            color=t["bench"], linewidth=2, zorder=2)
    ax.axhline(100, color=t["zero"], linewidth=1.0, zorder=1)
    style(ax, t, title=f"Live book vs BTC buy-and-hold, {lo} to {hi}",
          ylabel="index, 100 at start", zero_line=False)
    ax.annotate(f"book  {eq[-1][1]:.0f}", (days[-1], eq[-1][1]), color=t["book"],
                fontsize=10, fontweight="600", xytext=(8, 0), textcoords="offset points",
                va="center")
    ax.annotate(f"BTC  {bench[-1][1]:.0f}", (bench[-1][0], bench[-1][1]), color=t["bench"],
                fontsize=10, fontweight="600", xytext=(8, 0), textcoords="offset points",
                va="center")
    ax.legend(["Live book (net of fees)", "BTC buy-and-hold"], frameon=False,
              labelcolor=t["ink2"], fontsize=9, loc="upper left")
    ax.set_xlim(lo, hi)
    ax.margins(x=0.10)
    save(fig, "equity_curve", mode)

    # 2 --- underwater -----------------------------------------------------
    peak, uw = -1e18, []
    for d, v in eq:
        peak = max(peak, v)
        uw.append((d, (v / peak - 1) * 100))
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.fill_between([d for d, _ in uw], [v for _, v in uw], 0,
                    color=t["book"], alpha=0.22, linewidth=0, zorder=2)
    ax.plot([d for d, _ in uw], [v for _, v in uw], color=t["book"], linewidth=1.6, zorder=3)
    trough = min(uw, key=lambda x: x[1])
    style(ax, t, title="Drawdown from running peak", ylabel="% below peak")
    ax.yaxis.set_major_formatter(PCT)
    ax.set_xlim(lo, hi)
    # The label goes UP into the shaded area, never down: below the trough is
    # where the date ticks live, and the first version printed the two on top of
    # each other.
    ax.set_ylim(trough[1] * 1.08, 1.5)
    ax.annotate(f"{trough[1]:.1f}%  {trough[0]}", xy=trough,
                xytext=(14, 34), textcoords="offset points",
                color=t["ink"], fontsize=9.5, fontweight="600", ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=t["zero"], linewidth=1,
                                shrinkA=0, shrinkB=4))
    save(fig, "underwater", mode)

    # 3 --- monthly, book vs benchmark, one shared % axis -------------------
    bm: dict[str, list[float]] = {}
    for d, v in eq:
        bm.setdefault(f"{d:%Y-%m}", []).append(v)
    months = sorted(bm)
    book_m, prev = [], 100.0
    for m in months:
        book_m.append((bm[m][-1] / prev - 1) * 100)
        prev = bm[m][-1]
    bmm: dict[str, list[float]] = {}
    for d, v in bench:
        bmm.setdefault(f"{d:%Y-%m}", []).append(v)
    bench_m, prev = [], bench[0][1]
    for m in months:
        bench_m.append((bmm[m][-1] / prev - 1) * 100)
        prev = bmm[m][-1]

    x = range(len(months))
    fig, ax = plt.subplots(figsize=(9, 4.0))
    b1 = ax.bar([i - 0.21 for i in x], book_m, width=0.38, color=t["book"], zorder=3)
    b2 = ax.bar([i + 0.21 for i in x], bench_m, width=0.38, color=t["bench"], zorder=3)
    style(ax, t, title="Monthly return, book net of fees vs BTC", ylabel="% in month")
    ax.set_xticks(list(x))
    ax.set_xticklabels(months, fontsize=9)
    ax.yaxis.set_major_formatter(PCT)
    # Explicit handles. Passing labels alone let the zero-line Line2D claim the
    # first legend slot, which shipped a chart whose key said blue = BTC.
    ax.legend([b1, b2], ["Live book", "BTC"], frameon=False, labelcolor=t["ink2"],
              fontsize=9, loc="upper left")
    save(fig, "monthly_net", mode)

    # 4 --- distribution of outcomes, in R over the full documented book -----
    # R, not USDT. A desk thinks in units of risk, and a USDT axis on a book
    # whose position size grew 200x over the year mostly plots the size ramp.
    vals = sorted(r_multiples)
    fig, ax = plt.subplots(figsize=(9, 3.9))
    lo_e, hi_e = np.floor(min(vals) * 4) / 4, np.ceil(max(vals) * 4) / 4
    ax.hist(vals, bins=np.arange(lo_e, hi_e + 0.25, 0.25), color=t["book"], zorder=3)
    style(ax, t, title=f"Outcome per trade, in R. {len(vals)} trades, "
                       f"2025-03-09 to 2025-12-30", ylabel="trades", zero_line=False)
    ax.axvline(0, color=t["zero"], linewidth=1.0, zorder=2)
    ax.set_xlabel("R multiple, net", color=t["ink2"], fontsize=10)

    mean = sum(vals) / len(vals)
    med = vals[len(vals) // 2]
    top = ax.get_ylim()[1]
    ax.set_ylim(0, top * 1.22)
    # Stagger the two markers vertically. Drawn at the same height they overlapped
    # into an unreadable smear, which is what shipped the first time.
    for v, lab, y, dash in ((med, f"median {med:+.2f}R", 1.12, (0, (4, 3))),
                            (mean, f"mean {mean:+.2f}R", 1.02, (0, ()))):
        ax.axvline(v, color=t["bench"], linewidth=1.6, linestyle=dash, zorder=4)
        ax.annotate(lab, (v, top * y), color=t["bench"], fontsize=9, fontweight="600",
                    xytext=(7, 0), textcoords="offset points", va="center")
    best = max(vals)
    ax.annotate(f"best {best:+.2f}R", (best, top * 0.16), color=t["ink2"], fontsize=9,
                ha="right", xytext=(-6, 0), textcoords="offset points", va="center")
    save(fig, "r_distribution", mode)

    # 5 --- monthly R across the whole documented book ----------------------
    # The % chart above can only cover the venue window. This one covers the
    # ramp months too, which is where the process actually starts.
    months_r = sorted(monthly_r)
    vals_r = [monthly_r[m] for m in months_r]
    fig, ax = plt.subplots(figsize=(9, 3.9))
    ax.bar(range(len(months_r)), vals_r, width=0.62, color=t["book"], zorder=3)
    style(ax, t, title="Monthly result in R, whole documented book",
          ylabel="R in month")
    ax.set_xticks(range(len(months_r)))
    ax.set_xticklabels(months_r, fontsize=9, rotation=0)
    pad = max(abs(min(vals_r)), max(vals_r)) * 0.20
    ax.set_ylim(min(vals_r) - pad, max(vals_r) + pad)
    for i, v in enumerate(vals_r):
        ax.annotate(f"{v:+.1f}", (i, v), color=t["ink2"], fontsize=8.5, ha="center",
                    va="bottom" if v >= 0 else "top",
                    xytext=(0, 4 if v >= 0 else -4), textcoords="offset points")
    save(fig, "monthly_r", mode)

    return eq, trough


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--starting-capital", type=float, required=True)
    a = ap.parse_args()

    fills = load_fills(EXPORT_2026_05)
    daily, events, btc = daily_net(fills), realized_events(fills), load_btc()

    sheet, _ = load_sheet(ROOT / "private" / "raw" / "LiveTrading_2025_Latest.xlsx",
                          "Live 2025")
    r_multiples = [float(x) for x in sheet["R+/-"].dropna()]
    monthly_r = {str(k): float(v) for k, v in
                 sheet.groupby(sheet["entry"].dt.to_period("M"))["R+/-"].sum().items()}
    print(f"figures for capital {a.starting_capital:,.0f} USDT:")
    for mode in ("light", "dark"):
        eq, trough = build(mode, daily, events, a.starting_capital, btc,
                           r_multiples, monthly_r)
    print(f"\nbook  {eq[0][0]} .. {eq[-1][0]}   index {eq[-1][1]:.1f}  "
          f"({eq[-1][1]-100:+.1f}%)   max drawdown {trough[1]:.1f}% on {trough[0]}")
