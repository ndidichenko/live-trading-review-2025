"""Which export is which, and what zone its naive timestamps are in.

The KCEX CSV does not record its own timezone. Two exports of the same account
covering the same 3 months disagreed by exactly 3h on all 390 overlapping fills,
so the zone is a property of the export session, not of the account.

Each offset below was MEASURED, not assumed: taker fills execute at the touch,
so the recorded price should sit on the 1-minute candle of the true UTC minute.
Scanning candidate offsets and comparing |fill price - 1m close| gives a single
sharp winner per file (83% of fills within 0.15%, versus 7-20% for neighbours).
Reproduce with scripts/verify_timezone.py.
"""
from __future__ import annotations

from pathlib import Path

from .schema import SourceFile

PRIVATE = Path(__file__).resolve().parent.parent / "private" / "raw" / "kcex-csv"

EXPORT_2025_11 = SourceFile(
    path=str(PRIVATE / "Futures_Trade_History_20250801_20251101_117.csv"),
    tz_offset_hours=1,
    label="export_2025-11-01",
    notes="Pulled 2025-11-01. Covers 2025-08-01..2025-10-31. Stamps are UTC+1.",
)

EXPORT_2026_05 = SourceFile(
    path=str(PRIVATE / "Futures_Trade_History_20250519_20260101_537.csv"),
    tz_offset_hours=4,
    label="export_2026-05-18",
    notes=(
        "Pulled 2026-05-18. Filename claims 2025-05-19..2026-01-01 but the rows "
        "run 2025-06-02..2025-12-30. Stamps are UTC+4, three hours later than the "
        "2025-11 export: the venue stamps in the exporting session's local zone."
    ),
)

ALL = [EXPORT_2025_11, EXPORT_2026_05]
