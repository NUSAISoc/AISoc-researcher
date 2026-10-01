"""Readable canonical records and a deterministic generated index."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

RECORDS = "docs/workflow/records"
HISTORY = "docs/workflow/history/records"
MANIFEST = "docs/workflow/manifest.json"
INITIAL = {
    "evidence": "captured", "claim": "proposed", "gap": "identified",
    "opportunity": "proposed", "hypothesis": "draft", "campaign": "proposed",
    "run": "planned", "evaluation": "draft", "decision": "proposed",
}
TRANSITIONS = {
    "evidence": {"captured": {"reviewed"}, "reviewed": {"admitted", "excluded"}, "admitted": {"superseded"}, "excluded": set(), "superseded": set()},
    "claim": {"proposed": {"reviewed"}, "reviewed": {"accepted", "rejected"}, "accepted": set(), "rejected": set()},
    "gap": {"identified": {"reviewed"}, "reviewed": {"open", "dismissed"}, "open": {"resolved", "dismissed"}, "resolved": set(), "dismissed": set()},
    "opportunity": {"proposed": {"reviewed"}, "reviewed": {"selected", "declined"}, "selected": set(), "declined": set()},
    "hypothesis": {"draft": {"approved", "rejected"}, "approved": {"under_test"}, "under_test": {"evaluated"}, "evaluated": set(), "rejected": set()},
    "campaign": {"proposed": {"approved", "rejected"}, "approved": {"active", "cancelled"}, "active": {"completed", "cancelled"}, "completed": set(), "cancelled": set(), "rejected": set()},
    "run": {"planned": {"authorized", "cancelled"}, "authorized": {"running", "cancelled"}, "running": {"completed", "failed", "cancelled"}, "completed": set(), "failed": set(), "cancelled": set()},
    "evaluation": {"draft": {"reviewed"}, "reviewed": {"accepted", "rejected"}, "accepted": set(), "rejected": set()},
    "decision": {"proposed": {"approved", "rejected"}, "approved": {"superseded"}, "rejected": set(), "superseded": set()},
}
DETAILS = {
    "evidence": ("source", "locator", "reading_depth", "limitations"),
    "claim": ("statement",), "gap": ("description",), "opportunity": ("description",),
    "hypothesis": ("statement",), "campaign": ("protocol_ref", "stopping_rules"),
    "run": (), "evaluation": ("analysis_ref", "conclusion"), "decision": ("action", "reason"),
}
TERMINAL = {"excluded", "superseded", "rejected", "resolved", "dismissed", "declined", "evaluated", "completed", "failed", "cancelled"}
RELATIONS = {"evidence", "decision", "hypothesis", "campaign", "run", "gap", "target", "supersedes"}
APPROVED = {
    "claim": {"accepted"}, "gap": {"resolved", "dismissed"}, "opportunity": {"selected"},
    "hypothesis": {"approved", "under_test", "evaluated"},
    "campaign": {"approved", "active", "completed", "cancelled"},
    "run": {"authorized", "running", "completed", "failed"}, "evaluation": {"accepted"},
}


class WorkflowError(ValueError):
    """A workflow constraint failed; callers must not partially accept the change."""


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    """Reject traversal, repository internals, and every symlink component."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise WorkflowError("invalid relative path")
    parts = PurePosixPath(relative).parts
    if PurePosixPath(relative).is_absolute() or any(p in {"..", ".git"} for p in parts) or str(PurePosixPath(relative)) != relative:
        raise WorkflowError(f"unsafe path: {relative}")
    root = root.resolve()
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise WorkflowError(f"symlink path: {relative}")
    if path.resolve() == root or not path.resolve().is_relative_to(root):
        raise WorkflowError(f"path escapes repository: {relative}")
    return path


def encode_record(metadata: dict, body: str) -> str:
    return "```json\n" + canonical_json(metadata) + "```\n\n" + body


@dataclass(frozen=True)
class Record:
    path: str
    text: str
    metadata: dict

    @property
    def key(self):
        return self.metadata["id"], self.metadata["revision"]

    @property
    def digest(self):
        return sha256(self.text)

    @property
    def active(self):
        return not self.metadata.get("retirement") and self.metadata["status"] not in TERMINAL


def parse_record(text: str, path: str = "<record>") -> Record:
    match = re.match(r"\A```json\n(.*?)\n```\n", text, re.DOTALL)
    if not match:
        raise WorkflowError(f"{path}: missing fenced JSON metadata")
    try:
        meta = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"{path}: invalid JSON metadata") from exc
    if not isinstance(meta, dict):
        raise WorkflowError(f"{path}: metadata must be an object")
    required = {"id", "type", "status", "owner", "revision", "created_at", "links", "details"}
    if required - meta.keys() or meta.keys() - required - {"retirement"}:
        raise WorkflowError(f"{path}: missing or unknown metadata fields")
    if not isinstance(meta["id"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", meta["id"]):
        raise WorkflowError(f"{path}: invalid id")
    if type(meta["revision"]) is not int or meta["revision"] < 1:
        raise WorkflowError(f"{path}: revision must be a positive integer")
    kind = meta["type"]
    if not isinstance(kind, str) or kind not in TRANSITIONS:
        raise WorkflowError(f"{path}: unknown record type")
    if not isinstance(meta["status"], str) or meta["status"] not in TRANSITIONS[kind]:
        raise WorkflowError(f"{path}: invalid status for {kind}")
    if not isinstance(meta["owner"], str) or not meta["owner"].strip():
        raise WorkflowError(f"{path}: owner required")
    try:
        stamp = datetime.fromisoformat(meta["created_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("timezone required")
    except (ValueError, TypeError, AttributeError) as exc:
        raise WorkflowError(f"{path}: invalid created_at") from exc
    if not isinstance(meta["details"], dict):
        raise WorkflowError(f"{path}: details must be an object")
    for field in DETAILS[kind]:
        if not isinstance(meta["details"].get(field), str) or not meta["details"][field].strip():
            raise WorkflowError(f"{path}: {field} detail required")
    if kind == "evidence" and meta["details"]["reading_depth"] not in {"full", "abstract", "artifact", "non-peer-reviewed"}:
        raise WorkflowError(f"{path}: invalid reading_depth")
    if kind == "evaluation" and meta["details"]["conclusion"] not in {"supports", "contradicts", "inconclusive"}:
        raise WorkflowError(f"{path}: invalid conclusion")
    if not isinstance(meta["links"], list):
        raise WorkflowError(f"{path}: links must be a list")
    for item in meta["links"]:
        _check_link(item, path)
    if "retirement" in meta:
        retirement = meta["retirement"]
        if not isinstance(retirement, dict) or set(retirement) != {"reason", "decision"} or not isinstance(retirement["reason"], str) or not retirement["reason"].strip():
            raise WorkflowError(f"{path}: retirement requires reason and decision")
        _check_link(retirement["decision"], path)
        if retirement["decision"]["relation"] != "decision":
            raise WorkflowError(f"{path}: retirement requires a decision link")
    return Record(path, text, meta)


def _check_link(item, path):
    if not isinstance(item, dict) or set(item) != {"relation", "id", "revision"}:
        raise WorkflowError(f"{path}: link requires relation, id, revision")
    if not isinstance(item["relation"], str) or item["relation"] not in RELATIONS or not isinstance(item["id"], str) or type(item["revision"]) is not int or item["revision"] < 1:
        raise WorkflowError(f"{path}: invalid link")


def read_record(root: Path, path: str) -> Record:
    return parse_record(safe_path(root, path).read_text(encoding="utf-8"), path)


@dataclass
class RecordSet:
    current: dict[str, Record]
    versions: dict[tuple[str, int], Record]


def _scan(root: Path, replacements: dict[str, str]) -> RecordSet:
    current, versions = {}, {}
    for prefix in (HISTORY, RECORDS):
        directory = safe_path(root, prefix)
        paths = {p.relative_to(root).as_posix() for p in directory.rglob("*.md")} if directory.exists() else set()
        paths.update(p for p in replacements if p.startswith(prefix + "/") and p.endswith(".md"))
        for path in sorted(paths):
            safe_path(root, path)
            rec = parse_record(replacements[path], path) if path in replacements else read_record(root, path)
            if rec.key in versions:
                raise WorkflowError(f"duplicate record revision: {rec.key}")
            versions[rec.key] = rec
            if prefix == RECORDS:
                if rec.metadata["id"] in current:
                    raise WorkflowError(f"duplicate current id: {rec.metadata['id']}")
                current[rec.metadata["id"]] = rec
            elif path != f"{HISTORY}/{rec.metadata['id']}/{rec.metadata['revision']}.md":
                raise WorkflowError(f"history path does not match revision: {path}")
    return RecordSet(current, versions)


def _decision(rec: Record, records: RecordSet, reference: dict):
    decision = records.versions.get((reference["id"], reference["revision"]))
    if decision is None or decision.metadata["type"] != "decision" or decision.metadata["status"] != "approved":
        raise WorkflowError(f"{rec.path}: missing approved decision")
    if not any(l["relation"] == "target" and (l["id"], l["revision"]) == rec.key for l in decision.metadata["links"]):
        raise WorkflowError(f"{rec.path}: decision must target the exact revision")


def validate_records(root: Path, replacements: dict[str, str] | None = None) -> RecordSet:
    root = root.resolve()
    replacements = replacements or {}
    records = _scan(root, replacements)
    for rec in records.versions.values():
        meta = rec.metadata
        relations = set()
        for item in meta["links"]:
            key = item["id"], item["revision"]
            target = records.versions.get(key)
            if target is None:
                raise WorkflowError(f"{rec.path}: missing revision {key}")
            relation = item["relation"]
            relations.add(relation)
            if relation not in {"target", "supersedes"} and target.metadata["type"] != relation:
                raise WorkflowError(f"{rec.path}: wrong link type for {relation}")
        kind, status = meta["type"], meta["status"]
        required = {"hypothesis": "evidence", "claim": "evidence", "gap": "evidence", "opportunity": "gap", "campaign": "hypothesis", "run": "campaign", "evaluation": "run", "decision": "target"}.get(kind)
        if required and required not in relations:
            raise WorkflowError(f"{rec.path}: {required} link required")
        if status in APPROVED.get(kind, set()):
            decisions = [l for l in meta["links"] if l["relation"] == "decision"]
            if not decisions:
                raise WorkflowError(f"{rec.path}: approved decision link required")
            for reference in decisions:
                _decision(rec, records, reference)
            for item in meta["links"]:
                if item["relation"] == "evidence" and records.versions[(item["id"], item["revision"])].metadata["status"] != "admitted":
                    raise WorkflowError(f"{rec.path}: approval requires admitted evidence")
        if meta.get("retirement"):
            _decision(rec, records, meta["retirement"]["decision"])
        if kind == "campaign":
            path = meta["details"]["protocol_ref"]
            if not safe_path(root, path).is_file() and path not in replacements:
                raise WorkflowError(f"{rec.path}: missing protocol reference")
            if status in APPROVED[kind]:
                for item in meta["links"]:
                    if item["relation"] == "hypothesis":
                        target = records.versions[(item["id"], item["revision"])]
                        if target.metadata["status"] not in APPROVED["hypothesis"]:
                            raise WorkflowError(f"{rec.path}: campaign requires approved hypothesis")
        if rec.active and records.current.get(meta["id"]) == rec and kind in {"campaign", "run"}:
            for item in meta["links"]:
                if item["relation"] in {"hypothesis", "campaign"} and records.current.get(item["id"], records.versions[(item["id"], item["revision"])]).metadata.get("retirement"):
                    raise WorkflowError(f"{rec.path}: active work references retired record")
        if kind == "run" and status in {"completed", "failed", "cancelled"} and meta["details"].get("run_id"):
            _check_run(root, rec, replacements)
        elif kind == "run" and status in {"completed", "failed"}:
            raise WorkflowError(f"{rec.path}: terminal run requires ledger/log references")
    return records


def _check_run(root, rec, replacements):
    detail = rec.metadata["details"]
    try:
        ledger = detail["ledger_ref"]
        log = detail["log_ref"]
        lp, rp = safe_path(root, ledger), safe_path(root, log)
        rows = list(csv.DictReader((replacements.get(ledger) or lp.read_text(encoding="utf-8")).splitlines()))
        matches = [r for r in rows if r.get("run_id") == detail["run_id"]]
        if len(matches) != 1:
            raise WorkflowError(f"{rec.path}: exactly one ledger row required")
        expected = {"completed": "ok", "failed": "error", "cancelled": "cancelled"}[rec.metadata["status"]]
        if matches[0].get("status") != expected:
            raise WorkflowError(f"{rec.path}: ledger status mismatch")
        if matches[0].get("synthetic") not in {"true", "false"}:
            raise WorkflowError(f"{rec.path}: ledger synthetic marker required")
        entries = [json.loads(line) for line in (replacements.get(log) or rp.read_text(encoding="utf-8")).splitlines() if line.strip()]
        if not entries or not log.endswith("/" + detail["run_id"] + ".jsonl"):
            raise WorkflowError(f"{rec.path}: missing or incorrect run log")
    except (KeyError, OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"{rec.path}: missing or invalid ledger/log reference") from exc


def validate_change(root: Path, replacements: dict[str, str], *, rollback=False) -> RecordSet:
    before = validate_records(root)
    staged = dict(replacements)
    for path, text in replacements.items():
        safe_path(root, path)
        if path.startswith(HISTORY + "/"):
            raise WorkflowError("audited record history cannot be proposed directly")
        if path.startswith(RECORDS + "/"):
            if not path.endswith(".md"):
                raise WorkflowError("current records must be Markdown")
            new = parse_record(text, path)
            old = before.current.get(new.metadata["id"])
            if old is None:
                if new.metadata["revision"] != 1 or new.metadata["status"] != INITIAL[new.metadata["type"]]:
                    raise WorkflowError(f"{path}: new record must use initial status and revision")
                if safe_path(root, path).exists():
                    raise WorkflowError(f"{path}: existing identity cannot change")
            else:
                a, b = old.metadata, new.metadata
                if old.path != path or a["type"] != b["type"] or b["revision"] != a["revision"] + 1:
                    raise WorkflowError(f"{path}: identity/type must be stable and revision must increment")
                if a["created_at"] != b["created_at"]:
                    raise WorkflowError(f"{path}: created_at cannot change")
                if not rollback and b["status"] != a["status"] and b["status"] not in TRANSITIONS[a["type"]][a["status"]]:
                    raise WorkflowError(f"{path}: invalid state transition")
                if a.get("retirement") and not rollback:
                    raise WorkflowError(f"{path}: retired record requires reviewed rollback")
                if a["type"] == "decision" and a["status"] != "proposed" and (b["status"] != "superseded" or a["details"] != b["details"] or a["links"] != b["links"]):
                    raise WorkflowError(f"{path}: approved/rejected decision history cannot be rewritten")
                if a["type"] == "run" and a["status"] in {"completed", "failed", "cancelled"}:
                    raise WorkflowError(f"{path}: terminal run cannot be rewritten; create another run")
                staged[f"{HISTORY}/{a['id']}/{a['revision']}.md"] = old.text
    return validate_records(root, staged)


def build_manifest(root: Path, replacements=None) -> dict:
    records = validate_records(root, replacements)
    return {"schema_version": 1, "records": [
        {"id": rec.metadata["id"], "type": rec.metadata["type"], "status": rec.metadata["status"],
         "owner": rec.metadata["owner"], "revision": rec.metadata["revision"], "path": rec.path,
         "sha256": rec.digest, "links": rec.metadata["links"], "active": rec.active}
        for _, rec in sorted(records.current.items())
    ]}


def write_manifest(root: Path):
    content = canonical_json(build_manifest(root))
    path = safe_path(root, MANIFEST)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def check_manifest(root: Path):
    path = safe_path(root, MANIFEST)
    if not path.is_file() or path.read_text(encoding="utf-8") != canonical_json(build_manifest(root)):
        raise WorkflowError("manifest is missing or stale; regenerate from canonical records")
