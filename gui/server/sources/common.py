"""Shared helpers for source readers.

Each source reader is independent. A reader that fails returns a SourceResult
with ok=False instead of raising, so one broken file never takes down the
overview or the other readers. Readers only read; none of them writes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional

NOT_TRACKED = {"tracked": False}


def unavailable(reason: str) -> dict:
    """Marker for a value whose source exists but could not be read."""
    return {"tracked": True, "available": False, "reason": reason}


@dataclass
class SourceResult:
    path: str
    ok: bool
    value: Any = None
    reason: str = ""
    warnings: List[str] = field(default_factory=list)


def read_text(path: Path) -> str:
    """Read a text file, tolerating CRLF line endings and a byte-order mark."""
    return path.read_text(encoding="utf-8-sig")


def guarded(rel_path: str, reader: Callable[[Path], Any], root: Path) -> SourceResult:
    """Run a reader and convert any failure into an ok=False result."""
    path = root / rel_path
    try:
        if not path.is_file():
            return SourceResult(rel_path, False, reason=f"{rel_path} not found")
        value = reader(path)
        if isinstance(value, SourceResult):
            return value
        return SourceResult(rel_path, True, value)
    except Exception as exc:  # noqa: BLE001 - isolation is the point
        return SourceResult(rel_path, False, reason=f"could not read {rel_path} ({type(exc).__name__})")


def is_template(text: str) -> bool:
    """True for placeholder text such as `<Author (Year), Title>`."""
    t = text.strip().strip("`").strip()
    return t.startswith("<") and t.endswith(">")


def file_mtime(path: Path) -> Optional[float]:
    try:
        return path.stat().st_mtime
    except OSError:
        return None
