"""Whether any study data has been entered in the result templates.

Only reports "has rows below the header" or not. It cannot tell whether data
was anonymised; that is recorded nowhere yet.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from .common import SourceResult, read_text

REL_PATHS = ("results/participants.csv", "results/measurements.csv")


def read(root: Path) -> SourceResult:
    has_data = False
    for rel in REL_PATHS:
        path = root / rel
        try:
            if not path.is_file():
                return SourceResult(rel, False, reason=f"{rel} not found")
            rows = [r for r in csv.reader(io.StringIO(read_text(path), newline="")) if any(c.strip() for c in r)]
        except Exception as exc:  # noqa: BLE001
            return SourceResult(rel, False, reason=f"could not read {rel} ({type(exc).__name__})")
        if len(rows) > 1:
            has_data = True
    return SourceResult(" and ".join(REL_PATHS), True, {"hasData": has_data})
