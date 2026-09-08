"""The run ledger and per-run result logs.

Every experiment run appends exactly one row to ``results/ledger.csv`` and
writes one JSON Lines log to ``results/logs/<run_id>.jsonl``. Together they are
the audit trail: a result that cannot be traced to a ledger row and a log does
not exist. The ledger writer never touches the results templates
(``participants.csv``, ``measurements.csv``) or ``docs/06``; promoting run
output into those files is a deliberate, human-reviewed step, never automatic.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping

from .config import RESULTS_DIR

LEDGER_PATH = RESULTS_DIR / "ledger.csv"
LOGS_DIR = RESULTS_DIR / "logs"

LEDGER_FIELDS = (
    "run_id",
    "timestamp_utc",
    "mode",
    "experiment",
    "config_hash",
    "synthetic",
    "num_records",
    "status",
    "notes",
)


def ensure_ledger(path: Path = LEDGER_PATH) -> None:
    """Create the ledger with its header row if it does not exist."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(LEDGER_FIELDS)


def append_ledger_row(row: Mapping[str, object], path: Path = LEDGER_PATH) -> None:
    """Append exactly one row to the ledger, in the fixed column order."""
    ensure_ledger(path)
    missing = [f for f in LEDGER_FIELDS if f not in row]
    if missing:
        raise ValueError(f"ledger row missing fields: {missing}")
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_FIELDS)
        writer.writerow({f: row[f] for f in LEDGER_FIELDS})


def write_log(run_id: str, records: Iterable[Mapping[str, object]], logs_dir: Path = LOGS_DIR) -> Path:
    """Write the per-run JSON Lines log and return its path."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{run_id}.jsonl"
    with log_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")
    return log_path
