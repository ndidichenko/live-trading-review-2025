"""The authoritative realized-PnL series: one record per CLOSING fill.

Why not round trips. FIFO grouping of these exports does not work, and the
reason is in the data rather than in the code: a 0.0528 BTC long opened
2025-06-23 is never closed, so from that date the long book never returns to
flat and every later position merges into one enormous "trip". Two more
residuals (0.1058 long, 0.4220 short) are still open at the end of the window,
and the window itself starts mid-position, so three early closes have no
matching open.

The venue, unlike a reconstruction, knows the entry it is closing against and
publishes `Closing PNL` on every closing fill. That is ground truth for realized
PnL and it is what this module uses. Round trips remain available in
`roundtrip.py` for hold-time and scale-in questions, flagged as approximate.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .schema import Fill, Side

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class RealizedEvent:
    """One closing fill. `gross_pnl_usdt` is the venue's own number."""

    ts: datetime
    symbol: str
    side: Side
    qty: Decimal
    price: Decimal
    gross_pnl_usdt: Decimal
    exit_fee_usdt: Decimal
    maker: bool
    source: str

    @property
    def notional_usdt(self) -> Decimal:
        return self.qty * self.price


def realized_events(fills: list[Fill]) -> list[RealizedEvent]:
    return [
        RealizedEvent(
            ts=f.ts, symbol=f.symbol, side=f.side, qty=f.qty, price=f.price,
            gross_pnl_usdt=f.closing_pnl_usdt, exit_fee_usdt=f.fee_usdt,
            maker=f.role.value == "maker", source=f.source,
        )
        for f in fills if f.action == "close"
    ]


def fees_by_period(fills: list[Fill], key=lambda f: f"{f.ts:%Y-%m}") -> dict[str, Decimal]:
    """ALL fees, entry and exit, bucketed by period.

    Net PnL is exact at the period level: sum(closing PNL) - sum(all fees).
    It is only approximate per trade, because an entry fee belongs to a position
    rather than to one closing fill. Do not divide this number by trade count and
    call the result a per-trade cost.
    """
    out: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for f in fills:
        out[key(f)] += f.fee_usdt
    return dict(out)


def daily_net(fills: list[Fill]) -> list[tuple[date, float]]:
    """Net PnL per UTC day: realized gross that day, minus every fee paid that day."""
    gross: dict[date, Decimal] = defaultdict(lambda: ZERO)
    fees: dict[date, Decimal] = defaultdict(lambda: ZERO)
    for f in fills:
        d = f.ts.date()
        fees[d] += f.fee_usdt
        if f.action == "close":
            gross[d] += f.closing_pnl_usdt
    days = sorted(set(gross) | set(fees))
    return [(d, float(gross[d] - fees[d])) for d in days]
