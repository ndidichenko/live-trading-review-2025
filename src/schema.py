"""Typed records that move between pipeline steps.

No raw dicts cross a step boundary. Every quantity has exactly one definition,
stated here, and provenance is a field rather than a naming convention.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class Role(str, Enum):
    MAKER = "maker"
    TAKER = "taker"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Fill:
    """One executed fill as the venue reported it.

    `ts` is ALWAYS tz-aware UTC. The raw KCEX CSV carries a naive local stamp
    whose zone is not in the file; `SourceFile.tz_offset_hours` supplies it and
    the loader converts. See docs/00-scope-and-definitions.md.
    """

    ts: datetime
    symbol: str
    action: str          # "open" | "close"
    side: Side           # side of the POSITION, not of the order
    qty: Decimal         # base units (BTC)
    price: Decimal
    fee_usdt: Decimal    # always positive = a cost
    closing_pnl_usdt: Decimal  # venue-reported, gross of this fill's fee
    role: Role
    source: str          # provenance: which export file this row came from

    def __post_init__(self) -> None:
        if self.ts.tzinfo is None:
            raise ValueError(f"Fill.ts must be tz-aware UTC, got naive {self.ts!r}")
        if self.ts.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError(f"Fill.ts must be UTC, got offset {self.ts.utcoffset()!r}")


@dataclass(frozen=True, slots=True)
class RoundTrip:
    """A position opened and fully closed. The unit a desk actually reviews.

    A round trip may span many fills on both legs (scale-in, partial exits).
    """

    symbol: str
    side: Side
    opened_at: datetime
    closed_at: datetime
    qty: Decimal              # total base units opened
    avg_entry: Decimal
    avg_exit: Decimal
    gross_pnl_usdt: Decimal   # sum of venue closing PNL across the closing fills
    fees_usdt: Decimal        # entry + exit fees attributed to this round trip
    n_entry_fills: int
    n_exit_fills: int
    maker_fills: int
    taker_fills: int
    source: str

    @property
    def net_pnl_usdt(self) -> Decimal:
        return self.gross_pnl_usdt - self.fees_usdt

    @property
    def hold_seconds(self) -> float:
        return (self.closed_at - self.opened_at).total_seconds()

    @property
    def notional_usdt(self) -> Decimal:
        return self.qty * self.avg_entry


@dataclass(slots=True)
class RiskAnnotation:
    """Founder-supplied risk context, joined onto a round trip by open timestamp.

    This CANNOT be derived from the exchange export. Leverage on KCEX is a
    margin setting, not a risk setting: size came from stop distance, so R is
    only knowable from the manual log.
    """

    opened_at: datetime
    planned_risk_usdt: Decimal | None = None
    planned_risk_pct: Decimal | None = None
    stop_price: Decimal | None = None
    strategy_tag: str | None = None     # opaque sleeve label: A / B / C
    rule_violation: bool = False
    note: str = ""


@dataclass(slots=True)
class AnnotatedTrade:
    """A round trip plus whatever risk context exists for it."""

    trip: RoundTrip
    risk: RiskAnnotation | None = None

    @property
    def r_multiple(self) -> Decimal | None:
        """Net PnL expressed in units of planned risk. None when unknown.

        Deliberately returns None rather than a fallback: an R number computed
        from a guessed denominator is worse than no R number.
        """
        if self.risk is None or not self.risk.planned_risk_usdt:
            return None
        return self.trip.net_pnl_usdt / self.risk.planned_risk_usdt


@dataclass(slots=True)
class SourceFile:
    """An export on disk plus the metadata the file itself does not carry."""

    path: str
    tz_offset_hours: int   # offset of the naive stamps in the file, vs UTC
    label: str
    notes: str = ""
    skipped_rows: list[str] = field(default_factory=list)
