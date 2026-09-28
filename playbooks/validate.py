#!/usr/bin/env python3
"""Validate the community research-playbook registry and emit its index.

Stdlib only. Default mode validates every entry; --emit-index (re)writes
playbooks/registry.json deterministically. See playbooks/SCHEMA.md.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

EVIDENCE_STATUSES = {"experimental", "emerging", "established", "deprecated"}
REQUIRED_SECTIONS = [
    "Purpose", "When to use (applicability conditions)", "Inputs", "Procedure",
    "Expected artifacts", "Failure modes", "Evidence and validation status",
    "Limitations", "Compatibility", "Citations",
]
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RANGE_RE = re.compile(r"^(>=|<=|==|>|<|~|\^)?\d+\.\d+\.\d+$")
LIST_KEYS = {"lifecycle_stages", "authors", "citations"}


def content_digest(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _parse_scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def _parse_flow_list(raw: str) -> list[str]:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(item) for item in inner.split(",")]


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError("frontmatter must start with '---'")
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        raise ValueError("frontmatter is not terminated by '---'")
    header = parts[0][3:].lstrip("\n")
    body = parts[1].split("\n", 1)[1] if "\n" in parts[1] else ""
    fm: dict = {}
    pending_key: str | None = None
    for line in header.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if pending_key and line.lstrip().startswith("- "):
            fm.setdefault(pending_key, []).append(_parse_scalar(line.split("- ", 1)[1]))
            continue
        pending_key = None
        if ":" not in line:
            raise ValueError(f"unparseable frontmatter line: {line!r}")
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key in LIST_KEYS:
            if val.startswith("["):
                fm[key] = _parse_flow_list(val)
            elif val == "":
                pending_key = key
                fm[key] = []
            else:
                fm[key] = [_parse_scalar(val)]
        else:
            fm[key] = _parse_scalar(val)
    return fm, body


def docs_stems(repo_root: Path) -> set[str]:
    return {p.stem for p in (repo_root / "docs").glob("*.md")}


def validate_entry(path: Path, stems: set[str]) -> list[str]:
    rel = path.as_posix()
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        fm, body = parse_frontmatter(text)
    except ValueError as exc:
        return [f"{rel}: {exc}"]

    for key in ("id", "version", "title", "evidence_status", "compatibility",
                "authors", "license", "citations"):
        if key not in fm:
            errors.append(f"{rel}: missing required key '{key}'")

    id_ = fm.get("id", "")
    if id_ and not ID_RE.match(id_):
        errors.append(f"{rel}: id '{id_}' is not kebab-case")
    if id_ and path.parent.name != id_:
        errors.append(f"{rel}: id '{id_}' must equal parent directory '{path.parent.name}'")

    ver = fm.get("version", "")
    if ver and not SEMVER_RE.match(ver):
        errors.append(f"{rel}: version '{ver}' is not semver MAJOR.MINOR.PATCH")
    if ver and path.name != f"{ver}.md":
        errors.append(f"{rel}: filename must equal version ('{ver}.md')")

    status = fm.get("evidence_status", "")
    if status and status not in EVIDENCE_STATUSES:
        errors.append(f"{rel}: evidence_status '{status}' not in {sorted(EVIDENCE_STATUSES)}")
    if status == "established" and not fm.get("citations"):
        errors.append(f"{rel}: evidence_status 'established' requires non-empty citations")

    for stem in fm.get("lifecycle_stages", []):
        if stem not in stems:
            errors.append(f"{rel}: lifecycle_stage '{stem}' is not a docs/NN-name.md stem")

    compat = fm.get("compatibility", "")
    if compat and not RANGE_RE.match(compat):
        errors.append(f"{rel}: compatibility '{compat}' is not a valid semver range")

    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in body:
            errors.append(f"{rel}: missing required body section '## {section}'")

    for field in ("publisher", "key_id", "signature"):
        if field in fm and not isinstance(fm[field], str):
            errors.append(f"{rel}: reserved field '{field}' must be a string")

    return errors


def discover_entries(repo_root: Path) -> list[Path]:
    root = repo_root / "playbooks" / "entries"
    return sorted(root.glob("*/*.md")) if root.exists() else []


def load_deprecations(repo_root: Path) -> dict[tuple[str, str], dict]:
    """Read the hand-maintained deprecation ledger, keyed by (id, version).

    Deprecation cannot live in the entry file: a published file is immutable, so
    editing it (or its evidence_status) to mark it deprecated would break the
    content digest. The ledger is the one hand-edited source; --emit-index
    projects it into registry.json. An absent file means no deprecations.
    """
    path = repo_root / "playbooks" / "deprecations.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[tuple[str, str], dict] = {}
    for item in data.get("deprecations", []):
        result[(item.get("id", ""), item.get("version", ""))] = {
            "since": item.get("since"),
            "reason": item.get("reason"),
            "superseded_by": item.get("superseded_by"),
        }
    return result


def validate_deprecations(repo_root: Path, valid_pairs: set[tuple[str, str]]) -> list[str]:
    rel = "playbooks/deprecations.json"
    path = repo_root / "playbooks" / "deprecations.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{rel}: invalid JSON ({exc})"]
    errors: list[str] = []
    if data.get("schemaVersion") != 1:
        errors.append(f"{rel}: schemaVersion must be 1")
    items = data.get("deprecations", [])
    if not isinstance(items, list):
        return errors + [f"{rel}: 'deprecations' must be a list"]
    seen: set[tuple[str, str]] = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{rel}: deprecation #{i} must be an object")
            continue
        for req in ("id", "version", "since", "reason"):
            if not isinstance(item.get(req), str) or not item.get(req):
                errors.append(f"{rel}: deprecation #{i} missing required string '{req}'")
        sup = item.get("superseded_by")
        if sup is not None and not isinstance(sup, str):
            errors.append(f"{rel}: deprecation #{i} 'superseded_by' must be a string or null")
        id_, ver = item.get("id"), item.get("version")
        key = (id_, ver)
        if key in seen:
            errors.append(f"{rel}: duplicate deprecation for {id_}@{ver}")
        seen.add(key)
        if isinstance(id_, str) and isinstance(ver, str) and key not in valid_pairs:
            errors.append(f"{rel}: deprecation references unknown entry {id_}@{ver}")
    return errors


def build_index(repo_root: Path) -> dict:
    deprecations = load_deprecations(repo_root)
    entries = []
    for path in discover_entries(repo_root):
        text = path.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        dep = deprecations.get((fm["id"], fm["version"]))
        entries.append({
            "id": fm["id"],
            "version": fm["version"],
            "path": path.relative_to(repo_root).as_posix(),
            "content_sha256": content_digest(text),
            "evidence_status": fm["evidence_status"],
            "deprecated": (
                {"since": dep["since"], "reason": dep["reason"],
                 "superseded_by": dep["superseded_by"]} if dep else None
            ),
        })
    entries.sort(key=lambda e: (e["id"], e["version"]))
    return {"schemaVersion": 1, "entries": entries}


def _dumps(index: dict) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def check_index(repo_root: Path) -> list[str]:
    """Fail if registry.json is not a byte-exact rebuild of the entry files.

    Catches digest drift, hand-edits, and single-sided add/remove of a pair. A
    coordinated deletion (a published file and its row removed together) stays
    self-consistent and is guarded by review + Git history, not here — see
    SCHEMA.md, "The generated index".
    """
    index_path = repo_root / "playbooks" / "registry.json"
    rebuilt = build_index(repo_root)
    if not index_path.exists():
        return ["playbooks/registry.json: missing (run validate.py --emit-index)"]
    committed = json.loads(index_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if _dumps(committed) != _dumps(rebuilt):
        errors.append("playbooks/registry.json: does not match rebuilt index "
                      "(digest drift, hand-edit, or removed/mutated published pair)")
    return errors


def main(argv: list[str], repo_root: Path = REPO_ROOT) -> int:
    stems = docs_stems(repo_root)
    errors: list[str] = []
    valid_pairs: set[tuple[str, str]] = set()
    for path in discover_entries(repo_root):
        errors.extend(validate_entry(path, stems))
        try:
            fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            if "id" in fm and "version" in fm:
                valid_pairs.add((fm["id"], fm["version"]))
        except ValueError:
            pass  # malformed entry already reported by validate_entry
    errors.extend(validate_deprecations(repo_root, valid_pairs))
    # Only touch the index once every entry parses and validates; building it
    # from malformed content would raise instead of reporting the actionable
    # `path: reason` errors already collected above.
    if not errors:
        index_path = repo_root / "playbooks" / "registry.json"
        if "--emit-index" in argv:
            index_path.write_text(_dumps(build_index(repo_root)), encoding="utf-8")
            print(f"Wrote {index_path.relative_to(repo_root).as_posix()}")
        else:
            errors.extend(check_index(repo_root))
    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
