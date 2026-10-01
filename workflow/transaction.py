"""Recoverable grouped writes, with conflict detection and exclusive application."""
from __future__ import annotations

import base64
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .records import WorkflowError, canonical_json, safe_path, sha256

JOURNAL = "docs/workflow/.transaction.json"
LOCK = "docs/workflow/.lock"


def replace_file(path: Path, content: bytes | None):
    if content is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".workflow-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(name, path.stat().st_mode & 0o777)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_bytes(root: Path, relative: str):
    path = safe_path(root, relative)
    return path.read_bytes() if path.exists() else None


def digest_file(root: Path, relative: str):
    value = read_bytes(root, relative)
    return sha256(value) if value is not None else None


@contextmanager
def locked(root: Path):
    path = safe_path(root, LOCK)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise WorkflowError("another workflow operation holds the lock; inspect/recover before retry") from exc
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        path.unlink(missing_ok=True)


def _encoded(value):
    return None if value is None else base64.b64encode(value).decode("ascii")


def commit_files(root: Path, files: dict[str, bytes]):
    if safe_path(root, JOURNAL).exists():
        raise WorkflowError("unfinished transaction; run recovery before applying another proposal")
    entries = [{"path": path, "before": _encoded(read_bytes(root, path)), "after": _encoded(content)} for path, content in sorted(files.items())]
    journal = {"schema_version": 1, "state": "prepared", "entries": entries}
    replace_file(safe_path(root, JOURNAL), canonical_json(journal).encode())
    for entry in entries:
        before = None if entry["before"] is None else base64.b64decode(entry["before"])
        if read_bytes(root, entry["path"]) != before:
            raise WorkflowError("transaction conflict; recover before retrying")
        replace_file(safe_path(root, entry["path"]), base64.b64decode(entry["after"]))
    journal["state"] = "committed"
    replace_file(safe_path(root, JOURNAL), canonical_json(journal).encode())
    safe_path(root, JOURNAL).unlink()


def recover(root: Path):
    path = safe_path(root, JOURNAL)
    lock = safe_path(root, LOCK)
    cleared_lock = False
    if lock.exists():
        try:
            pid = int(lock.read_text())
            if pid < 1:
                raise ValueError("invalid lock pid")
            os.kill(pid, 0)
        except ProcessLookupError:
            lock.unlink()
            cleared_lock = True
        except (ValueError, OSError, OverflowError) as exc:
            raise WorkflowError("cannot establish that the transaction lock is abandoned") from exc
        else:
            raise WorkflowError("transaction owner is still running")
    with locked(root):
        # Approval verification holds the lock before any write journal exists.
        if not path.exists():
            if cleared_lock:
                return "lock-cleared"
            raise WorkflowError("no transaction to recover")
        try:
            journal = json.loads(path.read_text())
            if journal["schema_version"] != 1 or journal["state"] not in {"prepared", "committed"}:
                raise WorkflowError("invalid transaction journal")
            entries = journal["entries"]
            decoded = []
            seen = set()
            for entry in entries:
                target = safe_path(root, entry["path"])
                if entry["path"] in seen or entry["path"] in {JOURNAL, LOCK}:
                    raise WorkflowError("invalid transaction target")
                seen.add(entry["path"])
                before = None if entry["before"] is None else base64.b64decode(entry["before"], validate=True)
                after = base64.b64decode(entry["after"], validate=True)
                current = read_bytes(root, entry["path"])
                if current not in (before, after):
                    raise WorkflowError(f"recovery conflict at {entry['path']}; preserve the concurrent edit")
                if journal["state"] == "committed" and current != after:
                    raise WorkflowError("committed transaction changed; recovery cannot overwrite it")
                decoded.append((target, before))
            if journal["state"] == "prepared":
                for target, before in reversed(decoded):
                    replace_file(target, before)
            path.unlink()
            return "transaction-recovered"
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, WorkflowError):
                raise
            raise WorkflowError("invalid transaction journal; preserve it for inspection") from exc
