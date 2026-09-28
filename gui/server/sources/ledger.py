"""Run ledger from results/ledger.csv, plus safe access to run logs.

The ledger is written by the experiment runner (experiments/ledger.py). This
reader does not import that package, so the two stay independent; it relies
only on the documented column names.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import List, Optional

from .common import SourceResult, guarded, read_text

REL_PATH = "results/ledger.csv"
LOGS_DIR = "results/logs"
REQUIRED = ("run_id", "timestamp_utc", "status")
RUN_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def _parse(path: Path):
    reader = csv.DictReader(io.StringIO(read_text(path), newline=""))
    missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
    if missing:
        return SourceResult(REL_PATH, False, reason=f"{REL_PATH} is missing columns: {', '.join(missing)}")
    rows: List[dict] = []
    warnings: List[str] = []
    for n, row in enumerate(reader, start=2):
        rid = (row.get("run_id") or "").strip()
        if not rid:
            continue
        if not RUN_ID.match(rid):
            warnings.append(f"{REL_PATH} line {n}: unusual run_id skipped")
            continue
        rows.append({k: (v or "").strip() for k, v in row.items() if k})
    return SourceResult(REL_PATH, True, rows, warnings=warnings)


def read(root: Path) -> SourceResult:
    return guarded(REL_PATH, _parse, root)


def log_path(root: Path, run_id: str, rows: List[dict]) -> Optional[Path]:
    """Return the log file for a run, only if the run is in the ledger and the file exists inside results/logs."""
    if not RUN_ID.match(run_id or ""):
        return None
    if run_id not in {r["run_id"] for r in rows}:
        return None
    logs = (root / LOGS_DIR).resolve()
    candidate = (logs / f"{run_id}.jsonl").resolve()
    if candidate.parent != logs or not candidate.is_file():
        return None
    return candidate
