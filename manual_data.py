"""Persistent storage for entries created through the dashboard's manual-entry form."""
import os
from pathlib import Path
import tempfile

import pandas as pd


MANUAL_ENTRY_COLUMNS = [
    "output", "indicator", "activity", "subindicator", "partner", "district",
    "municipality", "status", "activity_reached", "notes", "entry_date",
    "lead_agency", "source_row",
]


def load_manual_entries(path):
    """Load dashboard-entered rows without coupling them to a 5W workbook."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=MANUAL_ENTRY_COLUMNS)
    try:
        manual = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise RuntimeError(f"Could not read saved manual entries at {path}: {exc}") from exc
    if manual.empty:
        return pd.DataFrame(columns=MANUAL_ENTRY_COLUMNS)
    for column in MANUAL_ENTRY_COLUMNS:
        if column not in manual:
            manual[column] = pd.NA
    return manual


def save_manual_entry(entry, path):
    """Append one form entry with an atomic file replacement."""
    path = Path(path)
    existing = load_manual_entries(path)
    row = {column: entry.get(column, pd.NA) for column in MANUAL_ENTRY_COLUMNS}
    updated = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    _write_manual_entries(updated, path)


def delete_manual_entry(row_index, path):
    """Delete one saved entry by its zero-based row position."""
    path = Path(path)
    existing = load_manual_entries(path)
    if not isinstance(row_index, int) or isinstance(row_index, bool) or not 0 <= row_index < len(existing):
        raise IndexError(f"Manual entry row {row_index!r} does not exist in {path}.")
    updated = existing.drop(index=existing.index[row_index]).reset_index(drop=True)
    _write_manual_entries(updated, path)


def _write_manual_entries(entries, path):
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", suffix=".tmp",
            prefix=f".{path.name}.", dir=path.parent, delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            entries.to_csv(temporary_file, index=False)
        os.replace(temporary_path, path)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise RuntimeError(f"Could not update saved manual entries at {path}: {exc}") from exc
