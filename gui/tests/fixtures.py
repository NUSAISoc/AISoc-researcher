"""Builds small throwaway repositories for tests. Nothing touches the real repository."""
import tempfile
from pathlib import Path

LEDGER_HEADER = "run_id,timestamp_utc,mode,experiment,config_hash,synthetic,num_records,status,notes\n"

RQ_TEMPLATE = """# Research Question\r\n\r\n## The one main research question\r\n\r\n> `<Your one main research question goes here.>`\r\n\r\nMore text.\r\n"""
REFERENCES_TEMPLATE = """# References

## Relevant Citations for the Current Research

1. `<Author, A. (Year). Title. Venue. [full]>`

## All Readings Read So Far

1. `<Author, B. (Year). Title. Venue. [abstract]>`
"""
READING_TEMPLATE = """# Reading List

| Candidate | Why it may matter | Suggested order |
| --- | --- | --- |
| `<Author (Year), Title>` | `<what it might contribute>` | `<1, 2, ...>` |
"""


def make_repo(**overrides):
    """Create a template-like repository in a temp dir. Pass text to override files, or None to omit one."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    files = {
        "docs/03-research-question.md": RQ_TEMPLATE,
        "references.md": REFERENCES_TEMPLATE,
        "readingList.md": READING_TEMPLATE,
        "results/ledger.csv": LEDGER_HEADER,
        "results/participants.csv": "participant_code,condition,consent,withdrawn\n",
        "results/measurements.csv": "participant_code,condition,measure_name,timing,value\n",
    }
    files.update(overrides)
    for rel, text in files.items():
        if text is None:
            continue
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))
    (root / "results/logs").mkdir(parents=True, exist_ok=True)
    return tmp, root


def snapshot(root: Path, include_log: bool = False):
    """Every file with its bytes, to prove nothing was written. The dashboard's own
    central log (gui/.local/) is left out unless include_log is true."""
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and (include_log or ".local" not in p.relative_to(root).parts)}


_SEQ = [0]


def event(etype, actor_kind, actor_id, subject_type, sid, version, data=None, at="2026-09-28T01:00:00Z"):
    """An event in the dashboard's input format, as an external producer would write it."""
    _SEQ[0] += 1
    return {"v": 1, "id": f"e{_SEQ[0]}", "type": etype, "at": at,
            "actor": {"kind": actor_kind, "id": actor_id},
            "subject": {"type": subject_type, "id": sid, "version": version}, "data": data or {}}


def write_events(root: Path, events, rel="control/events.jsonl"):
    """Append events to an external event file (standing in for a producer)."""
    import json
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        for e in events:
            fh.write((e if isinstance(e, str) else json.dumps(e)) + "\n")
