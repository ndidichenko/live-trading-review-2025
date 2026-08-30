"""Desk metrics over a list of round trips.

Every function states its denominator. Where a quantity cannot be computed from
the exchange export alone (anything in units of R, anything as a percent of
equity), it returns None rather than substituting a plausible-looking proxy.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .schema import AnnotatedTrade, RoundTrip, Side

ZERO = Decimal(0)


def _f(x: Decimal | None) -> float | None:
    return None if x is None else float(x)


@dataclass(frozen=True, slots=True)
class Drawdown:
    """Peak-to-trough on a CUMULATIVE NET PnL curve in USDT.

    This is not a percent-of-equity drawdown. Percent requires the equity path,
    which requires deposits and withdrawals, which the order export does not
    contain. Reporting this number as a percentage would be the wrong unit.
    """

    max_dd_usdt: float
    peak_at: date | None
    trough_at: date | None
    recovered_at: date | None

    @property
    def recovered(self) -> bool:
        return self.recovered_at is not None


@dataclass(frozen=True, slots=True)
class Summary:
    n_trades: int
    first_close: date | None
    last_close: date | None
    gross_pnl_usdt: float
    fees_usdt: float
    net_pnl_usdt: float
    cost_drag: float | None          # fees / gross profit, when gross > 0
    win_rate: float | None
    profit_factor: float | None
    expectancy_usdt: float | None
    avg_win_usdt: float | None
    avg_loss_usdt: float | None
    payoff_ratio: float | None       # avg win / |avg loss|
    p05_net_usdt: float | None       # left tail of the trade distribution
    p95_net_usdt: float | None
    median_hold_hours: float | None
    maker_share: float | None
    n_long: int
    n_short: int
    # Populated only when a risk annotation supplies planned risk per trade.
    n_with_r: int = 0
    expectancy_r: float | None = None
    worst_trade_r: float | None = None


def summarize(trades: list[AnnotatedTrade]) -> Summary:
    trips = [t.trip for t in trades]
    if not trips:
        return Summary(0, None, None, 0.0, 0.0, 0.0, None, None, None, None,
                       None, None, None, None, None, None, None, 0, 0)

    nets = [float(t.net_pnl_usdt) for t in trips]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x < 0]
    gross = float(sum(t.gross_pnl_usdt for t in trips))
    fees = float(sum(t.fees_usdt for t in trips))
    gross_profit = sum(float(t.gross_pnl_usdt) for t in trips if t.gross_pnl_usdt > 0)

    maker = sum(t.maker_fills for t in trips)
    total_fills = maker + sum(t.taker_fills for t in trips)

    rs = [float(t.r_multiple) for t in trades if t.r_multiple is not None]

    return Summary(
        n_trades=len(trips),
        first_close=trips[0].closed_at.date(),
        last_close=trips[-1].closed_at.date(),
        gross_pnl_usdt=gross,
        fees_usdt=fees,
        net_pnl_usdt=gross - fees,
        cost_drag=(fees / gross_profit) if gross_profit > 0 else None,
        win_rate=len(wins) / len(nets),
        profit_factor=(sum(wins) / abs(sum(losses))) if losses else None,
        expectancy_usdt=statistics.fmean(nets),
        avg_win_usdt=statistics.fmean(wins) if wins else None,
        avg_loss_usdt=statistics.fmean(losses) if losses else None,
        payoff_ratio=(statistics.fmean(wins) / abs(statistics.fmean(losses)))
        if wins and losses else None,
        p05_net_usdt=_pct(nets, 5),
        p95_net_usdt=_pct(nets, 95),
        median_hold_hours=statistics.median(t.hold_seconds for t in trips) / 3600,
        maker_share=(maker / total_fills) if total_fills else None,
        n_long=sum(1 for t in trips if t.side is Side.LONG),
        n_short=sum(1 for t in trips if t.side is Side.SHORT),
        n_with_r=len(rs),
        expectancy_r=statistics.fmean(rs) if rs else None,
        worst_trade_r=min(rs) if rs else None,
    )


def _pct(xs: list[float], p: int) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    i = min(len(s) - 1, max(0, round(p / 100 * (len(s) - 1))))
    return s[i]


def cumulative_pnl(trips: list[RoundTrip]) -> list[tuple[date, float]]:
    """Cumulative NET PnL in USDT, one point per trade close, in order."""
    out, run = [], 0.0
    for t in sorted(trips, key=lambda x: x.closed_at):
        run += float(t.net_pnl_usdt)
        out.append((t.closed_at.date(), run))
    return out


def max_drawdown(curve: list[tuple[date, float]]) -> Drawdown:
    if not curve:
        return Drawdown(0.0, None, None, None)
    peak, peak_at = curve[0][1], curve[0][0]
    worst, p_at, t_at = 0.0, None, None
    for d, v in curve:
        if v > peak:
            peak, peak_at = v, d
        dd = peak - v
        if dd > worst:
            worst, p_at, t_at = dd, peak_at, d
    recovered_at = None
    if t_at is not None:
        for d, v in curve:
            if d > t_at and v >= peak_before(curve, t_at):
                recovered_at = d
                break
    return Drawdown(worst, p_at, t_at, recovered_at)


def peak_before(curve: list[tuple[date, float]], when: date) -> float:
    return max((v for d, v in curve if d <= when), default=0.0)


def by_month(trips: list[RoundTrip]) -> dict[str, dict[str, float]]:
    """Net, gross, fees and trade count keyed by close month (UTC)."""
    agg: dict[str, dict[str, float]] = defaultdict(
        lambda: {"gross_usdt": 0.0, "fees_usdt": 0.0, "net_usdt": 0.0,
                 "trades": 0, "wins": 0}
    )
    for t in trips:
        m = agg[f"{t.closed_at:%Y-%m}"]
        m["gross_usdt"] += float(t.gross_pnl_usdt)
        m["fees_usdt"] += float(t.fees_usdt)
        m["net_usdt"] += float(t.net_pnl_usdt)
        m["trades"] += 1
        m["wins"] += 1 if t.net_pnl_usdt > 0 else 0
    return dict(sorted(agg.items()))


def worst_day(trips: list[RoundTrip]) -> tuple[date, float] | None:
    if not trips:
        return None
    d: dict[date, float] = defaultdict(float)
    for t in trips:
        d[t.closed_at.date()] += float(t.net_pnl_usdt)
    return min(d.items(), key=lambda kv: kv[1])


def streaks(trips: list[RoundTrip]) -> dict[str, int]:
    """Longest consecutive win and loss runs, by close order."""
    best = {"win": 0, "loss": 0}
    cur, kind = 0, None
    for t in sorted(trips, key=lambda x: x.closed_at):
        k = "win" if t.net_pnl_usdt > 0 else "loss"
        cur = cur + 1 if k == kind else 1
        kind = k
        best[k] = max(best[k], cur)
    return best


# ---------------------------------------------------------------------------
# Realized-event metrics. These are the headline numbers: the unit is a closing
# fill and the PnL is the venue's own, so nothing here depends on reconstructing
# which entry a close belonged to.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RealizedSummary:
    n_closes: int
    first: date | None
    last: date | None
    gross_usdt: float
    fees_usdt: float          # ALL fees in the window, entry and exit
    net_usdt: float
    cost_drag: float          # all fees / gross profit
    win_rate: float
    profit_factor: float | None
    expectancy_gross_usdt: float
    avg_win_usdt: float | None
    avg_loss_usdt: float | None
    payoff_ratio: float | None
    p05_usdt: float
    p95_usdt: float
    largest_win_usdt: float
    largest_loss_usdt: float
    maker_share: float
    n_long: int
    n_short: int
    median_notional_usdt: float
    max_notional_usdt: float


def summarize_realized(events: list, total_fees_usdt: float) -> RealizedSummary:
    """`events` are RealizedEvent; `total_fees_usdt` covers entry fees too."""
    g = [float(e.gross_pnl_usdt) for e in events]
    wins = [x for x in g if x > 0]
    losses = [x for x in g if x < 0]
    gross_profit = sum(wins)
    notionals = [float(e.notional_usdt) for e in events]
    makers = sum(1 for e in events if e.maker)

    return RealizedSummary(
        n_closes=len(events),
        first=events[0].ts.date() if events else None,
        last=events[-1].ts.date() if events else None,
        gross_usdt=sum(g),
        fees_usdt=total_fees_usdt,
        net_usdt=sum(g) - total_fees_usdt,
        cost_drag=(total_fees_usdt / gross_profit) if gross_profit > 0 else float("nan"),
        win_rate=len(wins) / len(g) if g else 0.0,
        profit_factor=(gross_profit / abs(sum(losses))) if losses else None,
        expectancy_gross_usdt=statistics.fmean(g) if g else 0.0,
        avg_win_usdt=statistics.fmean(wins) if wins else None,
        avg_loss_usdt=statistics.fmean(losses) if losses else None,
        payoff_ratio=(statistics.fmean(wins) / abs(statistics.fmean(losses)))
        if wins and losses else None,
        p05_usdt=_pct(g, 5) or 0.0,
        p95_usdt=_pct(g, 95) or 0.0,
        largest_win_usdt=max(g) if g else 0.0,
        largest_loss_usdt=min(g) if g else 0.0,
        maker_share=makers / len(events) if events else 0.0,
        n_long=sum(1 for e in events if e.side is Side.LONG),
        n_short=sum(1 for e in events if e.side is Side.SHORT),
        median_notional_usdt=statistics.median(notionals) if notionals else 0.0,
        max_notional_usdt=max(notionals) if notionals else 0.0,
    )


def equity_curve(daily: list[tuple[date, float]], starting_capital: float | None
                 ) -> list[tuple[date, float]] | None:
    """Compound daily net PnL onto a starting capital, indexed to 100.

    Returns None when starting capital is unknown, which is the honest answer:
    a percentage return has no meaning without the equity it is a percentage of,
    and the order export contains no deposits or withdrawals. Supply the figure
    from the manual log before quoting any percent.
    """
    if not starting_capital or starting_capital <= 0:
        return None
    eq, out = starting_capital, []
    for d, pnl in daily:
        eq += pnl
        out.append((d, eq / starting_capital * 100))
    return out


def cumulative_daily(daily: list[tuple[date, float]]) -> list[tuple[date, float]]:
    out, run = [], 0.0
    for d, v in daily:
        run += v
        out.append((d, run))
    return out
