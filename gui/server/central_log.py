"""The dashboard's central log: one local, append-only file that keeps everything
the dashboard has received or done.

Location: gui/.local/log.jsonl (gui/.gitignore keeps it out of git).

What goes in, one JSON record per line:
- "event":       a well-formed event received from an external source, either
                 imported from an event file (default control/events.jsonl) or
                 sent to POST /api/logs;
- "invalid":     something a source sent that was not a well-formed event, kept
                 with the reason so nothing is silently lost;
- "interaction": every command a researcher sent from the dashboard, with the
                 reply it got.

Records are never edited or removed. An event is stored once even if it
arrives again (same event id), so re-reading a source or a retry is harmless.
If a source file is later edited, rotated or deleted, what was already
imported stays here.

Record shape:
    {"v": 1, "logId": "...", "loggedAt": "2026-09-28T13:10:02Z", "source": "file:control/events.jsonl",
     "kind": "event", "entry": {...}}
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .event_format import check

RECORD_VERSION = 1
MAX_RAW = 2000


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_records(path: Path) -> List[Dict[str, Any]]:
    """All readable records, oldest first. Unreadable lines are skipped."""
    if not path.is_file():
        return []
    out = []
    with open(path, "rb") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(rec, dict) and rec.get("kind") in ("event", "invalid", "interaction"):
                out.append(rec)
    return out


class CentralLog:
    """Single writer for the central log. Thread-safe within the server process."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        # per source file: (bytes already imported, fingerprint of what those bytes started with)
        self._offsets: Dict[str, tuple] = {}
        self._seen: Optional[set] = None

    # ---------- writing ----------
    def _append(self, records: Iterable[Dict[str, Any]]) -> None:
        data = b"".join((json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8") for r in records)
        if not data:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)

    def _record(self, source: str, kind: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {"v": RECORD_VERSION, "logId": uuid.uuid4().hex, "loggedAt": _now(), "source": source, "kind": kind, "entry": entry}

    def _seen_ids(self) -> set:
        if self._seen is None:
            self._seen = {r["entry"].get("id") for r in read_records(self.path) if r["kind"] == "event"}
        return self._seen

    # ---------- inputs ----------
    def add_events(self, source: str, items: List[Any]) -> Dict[str, Any]:
        """Store events from a source. Returns counts and the reasons for rejected items."""
        accepted, duplicates, rejected, records = 0, 0, [], []
        with self._lock:
            seen = self._seen_ids()
            for i, item in enumerate(items):
                ok, reason = check(item)
                if not ok:
                    raw = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False, default=str)
                    records.append(self._record(source, "invalid", {"raw": raw[:MAX_RAW], "reason": reason}))
                    rejected.append({"index": i, "reason": reason})
                    continue
                if item["id"] in seen:
                    duplicates += 1
                    continue
                item = dict(item, data=item.get("data", {}))
                seen.add(item["id"])
                records.append(self._record(source, "event", item))
                accepted += 1
            self._append(records)
        return {"accepted": accepted, "duplicates": duplicates, "rejected": rejected}

    def import_file(self, root: Path, rel: str) -> Dict[str, Any]:
        """Copy new complete lines from an external event file. Never writes to that file."""
        path = root / rel
        if not path.is_file():
            return {"accepted": 0, "duplicates": 0, "rejected": []}
        offset, fingerprint = self._offsets.get(rel, (0, ""))
        with open(path, "rb") as fh:
            head = fh.read(min(offset, 4096)) if offset else b""
            if offset and (len(head) < min(offset, 4096) or hashlib.sha256(head).hexdigest() != fingerprint):
                offset = 0  # the file was replaced or rewritten: read it again; duplicates are skipped
            fh.seek(offset)
            chunk = fh.read()
            end = chunk.rfind(b"\n")
            if end < 0:
                return {"accepted": 0, "duplicates": 0, "rejected": []}  # no complete line yet
            new_offset = offset + end + 1
            fh.seek(0)
            fingerprint = hashlib.sha256(fh.read(min(new_offset, 4096))).hexdigest()
        self._offsets[rel] = (new_offset, fingerprint)
        items: List[Any] = []
        for raw in chunk[: end + 1].splitlines():
            if not raw.strip():
                continue
            try:
                items.append(json.loads(raw.decode("utf-8")))
            except (ValueError, UnicodeDecodeError):
                items.append(raw.decode("utf-8", "replace"))
        return self.add_events(f"file:{rel}", items)

    def add_interaction(self, entry: Dict[str, Any]) -> None:
        with self._lock:
            self._append([self._record("dashboard", "interaction", entry)])
