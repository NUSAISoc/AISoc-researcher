"""Change detection for the server-sent event stream.

A background thread checks the watched files' modification times. When any
change, it records one event per affected type and wakes waiting streams.
Events are kept in memory only; a reconnecting browser simply re-fetches.
"""
from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .sources import WATCHED, event_log
from .sources.common import file_mtime

# Which event type each watched file maps to.
EVENT_TYPES = {
    "docs/03-research-question.md": ["project.updated"],
    "results/participants.csv": ["project.updated"],
    "results/measurements.csv": ["project.updated"],
    "references.md": ["evidence.updated"],
    "readingList.md": ["evidence.updated"],
    "results/ledger.csv": ["run.updated", "audit.appended"],
    event_log.REL_PATH: ["finding.updated", "decision.updated", "run.updated", "audit.appended"],
}
MAX_KEPT = 200


def snapshot(root: Path) -> Dict[str, Optional[float]]:
    return {rel: file_mtime(root / rel) for rel in WATCHED}


def fingerprint(snap: Dict[str, Optional[float]]) -> str:
    raw = "|".join(f"{k}={v}" for k, v in sorted(snap.items()))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class Watcher:
    def __init__(self, root: Path, poll_seconds: float = 2.0, before_check=None) -> None:
        self.root = root
        self.poll = poll_seconds
        self.before_check = before_check  # e.g. import new lines from external event files
        self.cond = threading.Condition()
        self.events: List[Tuple[int, str]] = []
        self.last_id = 0
        self.snap = snapshot(root)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="gui-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self.cond:
            self.cond.notify_all()

    def check(self) -> None:
        if self.before_check:
            try:
                self.before_check()
            except Exception:  # noqa: BLE001 - an import problem must not stop change detection
                pass
        new = snapshot(self.root)
        changed = [k for k in new if new[k] != self.snap.get(k)]
        if not changed:
            return
        self.snap = new
        types = []
        for rel in changed:
            for t in EVENT_TYPES.get(rel, ["project.updated"]):
                if t not in types:
                    types.append(t)
        with self.cond:
            for t in types:
                self.last_id += 1
                self.events.append((self.last_id, t))
            del self.events[:-MAX_KEPT]
            self.cond.notify_all()

    def _run(self) -> None:
        while not self._stop.wait(self.poll):
            try:
                self.check()
            except Exception:  # noqa: BLE001 - keep watching
                pass

    def wait_after(self, last_seen: int, timeout: float) -> List[Tuple[int, str]]:
        with self.cond:
            if self.last_id <= last_seen and not self._stop.is_set():
                self.cond.wait(timeout)
            return [e for e in self.events if e[0] > last_seen]

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()
