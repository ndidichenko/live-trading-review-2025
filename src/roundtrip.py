"""Turn a stream of fills into round trips using FIFO inventory accounting.

A round trip opens when flat-to-nonzero and closes when the position returns to
zero. Scale-ins and partial exits stay inside one trip: the review unit is the
position, not the fill.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from .schema import Fill, Role, RoundTrip, Side

log = logging.getLogger(__name__)
ZERO = Decimal(0)


@dataclass
class _Lot:
    qty: Decimal
    price: Decimal
    fee: Decimal  # fee still attributable to the unconsumed part of this lot


@dataclass
class _Book:
    """Open inventory for one (symbol, side)."""

    lots: list[_Lot] = field(default_factory=list)
    opened_at: object = None
    entry_notional: Decimal = ZERO
    entry_qty: Decimal = ZERO
    entry_fees: Decimal = ZERO
    exit_notional: Decimal = ZERO
    exit_qty: Decimal = ZERO
    exit_fees: Decimal = ZERO
    gross_pnl: Decimal = ZERO
    n_entry: int = 0
    n_exit: int = 0
    maker: int = 0
    taker: int = 0

    @property
    def open_qty(self) -> Decimal:
        return sum((lot.qty for lot in self.lots), ZERO)


def _count_role(book: _Book, fill: Fill) -> None:
    if fill.role is Role.MAKER:
        book.maker += 1
    elif fill.role is Role.TAKER:
        book.taker += 1


def build_round_trips(
    fills: list[Fill], *, tolerance: Decimal = Decimal("1e-9")
) -> tuple[list[RoundTrip], list[str]]:
    """Return (round trips, warnings).

    Warnings are the reconciliation story, not noise: a close with no matching
    open means the export window starts mid-position. Those trips are still
    emitted, flagged in the warning list, and must be excluded from any
    per-trade statistic that assumes a known entry.
    """
    books: dict[tuple[str, Side], _Book] = {}
    trips: list[RoundTrip] = []
    warnings: list[str] = []

    for f in fills:
        key = (f.symbol, f.side)
        book = books.setdefault(key, _Book())

        if f.action == "open":
            if not book.lots and book.opened_at is None:
                book.opened_at = f.ts
            book.lots.append(_Lot(f.qty, f.price, f.fee_usdt))
            book.entry_notional += f.qty * f.price
            book.entry_qty += f.qty
            book.entry_fees += f.fee_usdt
            book.n_entry += 1
            _count_role(book, f)
            continue

        # close
        if book.opened_at is None:
            warnings.append(
                f"{f.ts:%Y-%m-%d %H:%M:%S}Z {f.symbol} {f.side.value}: "
                f"close of {f.qty} with no open in window (position predates export)"
            )
            book.opened_at = f.ts

        remaining = f.qty
        while remaining > tolerance and book.lots:
            lot = book.lots[0]
            take = min(lot.qty, remaining)
            lot.qty -= take
            remaining -= take
            if lot.qty <= tolerance:
                book.lots.pop(0)

        if remaining > tolerance:
            warnings.append(
                f"{f.ts:%Y-%m-%d %H:%M:%S}Z {f.symbol} {f.side.value}: "
                f"closed {remaining} more than was opened in window"
            )

        book.exit_notional += f.qty * f.price
        book.exit_qty += f.qty
        book.exit_fees += f.fee_usdt
        book.gross_pnl += f.closing_pnl_usdt
        book.n_exit += 1
        _count_role(book, f)

        if book.open_qty <= tolerance:
            qty = book.entry_qty or book.exit_qty
            trips.append(
                RoundTrip(
                    symbol=f.symbol,
                    side=f.side,
                    opened_at=book.opened_at,
                    closed_at=f.ts,
                    qty=qty,
                    avg_entry=(book.entry_notional / book.entry_qty) if book.entry_qty else ZERO,
                    avg_exit=(book.exit_notional / book.exit_qty) if book.exit_qty else ZERO,
                    gross_pnl_usdt=book.gross_pnl,
                    fees_usdt=book.entry_fees + book.exit_fees,
                    n_entry_fills=book.n_entry,
                    n_exit_fills=book.n_exit,
                    maker_fills=book.maker,
                    taker_fills=book.taker,
                    source=f.source,
                )
            )
            books[key] = _Book()

    for (sym, side), book in books.items():
        if book.open_qty > tolerance:
            warnings.append(
                f"{sym} {side.value}: {book.open_qty} still open at end of window "
                f"(opened {book.opened_at:%Y-%m-%d %H:%M:%S}Z), no round trip emitted"
            )

    trips.sort(key=lambda t: t.closed_at)
    log.info("built %d round trips, %d warnings", len(trips), len(warnings))
    return trips, warnings
