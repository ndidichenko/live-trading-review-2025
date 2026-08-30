"""Read the founder's manual trading sheet, repairing a date defect on the way.

THE DEFECT. The sheet records dates as MM/DD/YYYY text. Excel silently converted
the subset of cells where both parts are <= 12, and only that subset, into real
datetimes using a DD/MM locale. Unambiguous dates such as 11/25 could not be
read that way and survived as text. The result is a log where 14% of entry dates
and 43% of exit dates have their day and month transposed, while the rest are
correct, and nothing in the file marks which is which.

HOW IT SHOWS. 44 rows have an exit earlier than their entry, and five rows land
in January and February although the first trade in the book is 2025-03-09.

THE REPAIR. Cell storage type is the tell: a cell Excel converted is a datetime
object, a cell it left alone is a string. Every converted cell is transposed,
every string cell is parsed as MM/DD. The repair is verified rather than
assumed, by `validate()` below.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

COLUMNS = ["#", "ENTRY DATE", "EXIT DATE", "COIN", "DIRECTION ", "ENTRY ORDER TYPE",
           "AVG ENTRY", "STOP LOSS", "AVG EXIT", "RISK", "EXPECTED LOSS",
           "REALISED LOSS", "REALISED WIN", "DEVIATION", "POSITION SIZE", "R+/-",
           "EARLY EXIT REASON", "RULES?", "System", "Sizing", "Note"]
NUMERIC = ["RISK", "EXPECTED LOSS", "REALISED LOSS", "REALISED WIN",
           "DEVIATION", "POSITION SIZE", "R+/-"]
FIRST_TRADE = dt.date(2025, 3, 9)


@dataclass
class LoadReport:
    """What the loader had to fix. Publishable as-is; this is the audit trail."""

    rows: int = 0
    entry_transposed: int = 0
    exit_transposed: int = 0
    exit_before_entry_before: int = 0
    exit_before_entry_after: int = 0
    before_first_trade_before: int = 0
    before_first_trade_after: int = 0
    unparsed: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"manual sheet: {self.rows} trades\n"
            f"  entry dates repaired (day/month transposed): {self.entry_transposed}\n"
            f"  exit dates repaired:                         {self.exit_transposed}\n"
            f"  exit-before-entry   {self.exit_before_entry_before} -> {self.exit_before_entry_after}\n"
            f"  dated before the book opens  {self.before_first_trade_before} -> "
            f"{self.before_first_trade_after}\n"
            f"  unparsed cells: {len(self.unparsed)}"
        )


def _parse(cell) -> tuple[dt.datetime | None, bool]:
    """Return (timestamp, was_transposed).

    A datetime cell was converted by Excel under a DD/MM reading, so its day and
    month are swapped back. A string cell is read as MM/DD, which is what the
    sheet's own header says it is.
    """
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return None, False
    if isinstance(cell, dt.datetime):
        try:
            return cell.replace(month=cell.day, day=cell.month), True
        except ValueError:
            # day > 12: not ambiguous, so Excel's reading was already correct
            return cell, False
    ts = pd.to_datetime(str(cell), format="%m/%d/%Y %H:%M", errors="coerce")
    if pd.isna(ts):
        ts = pd.to_datetime(str(cell), errors="coerce")
    return (None if pd.isna(ts) else ts.to_pydatetime()), False


def load_sheet(path: Path, sheet: str) -> tuple[pd.DataFrame, LoadReport]:
    df = pd.read_excel(path, sheet_name=sheet, header=0).iloc[1:]
    df = df[[c for c in COLUMNS if c in df.columns]]
    df = df[pd.to_numeric(df["#"], errors="coerce").notna()].copy()
    df["#"] = pd.to_numeric(df["#"]).astype(int)
    # blank template rows carry a row number and nothing else
    df = df[df["ENTRY DATE"].notna()].copy()

    rep = LoadReport(rows=len(df))

    naive_e = pd.to_datetime(df["ENTRY DATE"], errors="coerce")
    naive_x = pd.to_datetime(df["EXIT DATE"], errors="coerce")
    rep.exit_before_entry_before = int((naive_x.notna() & (naive_x < naive_e)).sum())
    rep.before_first_trade_before = int((naive_e.dt.date < FIRST_TRADE).sum())

    for src, dst, counter in (("ENTRY DATE", "entry", "entry_transposed"),
                              ("EXIT DATE", "exit", "exit_transposed")):
        out, n = [], 0
        for cell in df[src]:
            ts, swapped = _parse(cell)
            n += swapped
            if ts is None and cell is not None and not (
                isinstance(cell, float) and pd.isna(cell)
            ):
                rep.unparsed.append(f"{src}: {cell!r}")
            out.append(ts)
        df[dst] = out
        setattr(rep, counter, n)

    for c in NUMERIC:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["net_usd"] = df["REALISED WIN"].fillna(0) - df["REALISED LOSS"].fillna(0)
    df["side"] = df["DIRECTION "].astype(str).str.strip().str.lower()
    df["sleeve_raw"] = df["System"].astype(str).str.strip()

    rep.exit_before_entry_after = int((df["exit"].notna() & (df["exit"] < df["entry"])).sum())
    rep.before_first_trade_after = int((df["entry"].dt.date < FIRST_TRADE).sum())
    df = df.sort_values("entry").reset_index(drop=True)
    log.info("%s", rep)
    return df, rep


def validate(df: pd.DataFrame, rep: LoadReport) -> list[str]:
    """Checks that must pass before any number from this sheet is published."""
    errs = []
    if rep.exit_before_entry_after:
        errs.append(f"{rep.exit_before_entry_after} rows still have exit before entry")
    if rep.before_first_trade_after:
        errs.append(f"{rep.before_first_trade_after} rows still predate {FIRST_TRADE}")
    if rep.unparsed:
        errs.append(f"{len(rep.unparsed)} date cells did not parse")
    gap = df["entry"].diff().dt.total_seconds()
    if (gap < -86400 * 21).sum():
        errs.append(f"{(gap < -86400*21).sum()} entries jump backwards by over 3 weeks")
    missing = df["R+/-"].isna().sum()
    if missing:
        errs.append(f"{missing} trades have no R value")
    return errs


ANON = {}


def anonymise_sleeve(name: str) -> str:
    """Map a sleeve name to an opaque label.

    Several of the founder's own labels describe the setup outright ("1H peak
    breakouts", "NY Open Sweeps", "CME Open"). Those names are the edge, so
    nothing derived from them may reach the public repo. Letters already in the
    sheet are kept; descriptive names are replaced by the next free letter.
    """
    key = (name or "").strip()
    if not key or key.lower() == "nan":
        return "unlabelled"
    if len(key) == 1 and key.isalpha():
        return key.upper()
    if key not in ANON:
        used = set(ANON.values())
        nxt = next(c for c in "NOPQRSTUVWXYZ" if c not in used)
        ANON[key] = nxt
    return ANON[key]
