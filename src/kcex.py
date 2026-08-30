"""Read KCEX futures exports into `Fill` records.

The export is a CSV of FILLS, newest first, with a naive timestamp. Two exports
of the same account and the same period were found to disagree by exactly
3 hours on all 390 overlapping rows, so the zone is a property of the export,
not of the account. It must be supplied per file and is never guessed.
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .schema import Fill, Role, Side, SourceFile

log = logging.getLogger(__name__)

_DIRECTION = {
    "Open Long": ("open", Side.LONG),
    "Close Long": ("close", Side.LONG),
    "Open Short": ("open", Side.SHORT),
    "Close Short": ("close", Side.SHORT),
}
_TS_FMT = "%Y-%m-%d %H:%M:%S"


def _amount(cell: str) -> Decimal:
    """'1.1926 BTC' -> Decimal('1.1926'); '13.09 USDT' -> Decimal('13.09')."""
    return Decimal(cell.strip().split()[0])


def load_fills(src: SourceFile) -> list[Fill]:
    """Parse one export. A bad row is logged and skipped, never fatal."""
    path = Path(src.path)
    if src.tz_offset_hours is None:  # pragma: no cover - guarded by dataclass
        raise ValueError(f"{path.name}: tz_offset_hours is required, refusing to guess")

    shift = timedelta(hours=src.tz_offset_hours)
    fills: list[Fill] = []

    with path.open(newline="", encoding="utf-8-sig") as fh:
        for lineno, row in enumerate(csv.DictReader(fh), start=2):
            try:
                action, side = _DIRECTION[row["Direction"].strip()]
                naive = datetime.strptime(row["Time"].strip(), _TS_FMT)
                fills.append(
                    Fill(
                        ts=(naive - shift).replace(tzinfo=timezone.utc),
                        symbol=row["Futures"].strip().replace(" ", ""),
                        action=action,
                        side=side,
                        qty=_amount(row["Amount"]),
                        price=Decimal(row["Order Price"].strip()),
                        fee_usdt=_amount(row["Fee"]),
                        closing_pnl_usdt=_amount(row["Closing PNL"]),
                        role=Role(row.get("Role", "").strip().lower() or "unknown"),
                        source=src.label,
                    )
                )
            except (KeyError, ValueError, InvalidOperation) as exc:
                msg = f"{path.name}:{lineno} skipped ({exc})"
                src.skipped_rows.append(msg)
                log.warning(msg)

    fills.sort(key=lambda f: f.ts)
    log.info("%s: %d fills, %s -> %s", src.label, len(fills),
             fills[0].ts if fills else "-", fills[-1].ts if fills else "-")
    return fills


def cross_check(base: list[Fill], other: list[Fill]) -> tuple[int, int, int]:
    """Compare a second export against the base over their overlapping window.

    Deliberately NOT a merge. Two fills of the same size at the same price in the
    same second are a split order, not a duplicate, so collapsing on
    (ts, action, side, qty, price) silently deleted 11 real fills the first time
    this was written. The wider export is the single source of truth; this
    function only answers whether the narrower one agrees with it.

    Returns (overlapping rows in base, matched, unmatched in other).
    """
    if not other:
        return (0, 0, 0)
    lo, hi = min(f.ts for f in other), max(f.ts for f in other)
    window = [f for f in base if lo <= f.ts <= hi]

    counts: dict[tuple, int] = {}
    for f in window:
        k = (f.ts, f.action, f.side, f.qty, f.price)
        counts[k] = counts.get(k, 0) + 1

    matched = 0
    for f in other:
        k = (f.ts, f.action, f.side, f.qty, f.price)
        if counts.get(k, 0) > 0:
            counts[k] -= 1
            matched += 1

    unmatched = len(other) - matched
    log.info("cross-check: %d rows in base window, %d matched, %d unmatched",
             len(window), matched, unmatched)
    return (len(window), matched, unmatched)
