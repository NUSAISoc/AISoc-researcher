"""Reads the dashboard's central log (gui/.local/log.jsonl) for display.

Read-only. Returns events and interactions, plus warnings for anything that
arrived malformed. A missing log means nothing has been received yet.
"""
from __future__ import annotations

from pathlib import Path

from ..central_log import read_records
from .common import SourceResult

REL_PATH = "gui/.local/log.jsonl"


def read(root: Path, rel_path: str = REL_PATH) -> SourceResult:
    try:
        records = read_records(root / rel_path)
    except OSError as exc:
        return SourceResult(rel_path, False, reason=f"could not read {rel_path} ({type(exc).__name__})")
    events = [r["entry"] for r in records if r["kind"] == "event"]
    interactions = [r for r in records if r["kind"] == "interaction"]
    invalid = [r for r in records if r["kind"] == "invalid"]
    warnings = []
    if invalid:
        last = invalid[-1]
        warnings.append(f"{len(invalid)} malformed item(s) from sources were kept in the log but not shown "
                        f"(latest from {last.get('source')}: {last['entry'].get('reason')})")
    return SourceResult(rel_path, True, {"events": events, "interactions": interactions}, warnings=warnings)
