"""Exact proposals, external human review, and recoverable accepted changes."""
from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from pathlib import Path

from .records import (HISTORY, ARTIFACT_HISTORY, RUN_EVIDENCE, MANIFEST, RECORDS, INITIAL, TRANSITIONS, WorkflowError, build_manifest, canonical_json,
                      encode_record, parse_record, record_body, load_json, safe_path, sha256, validate_change, validate_records)
from .reviews import POLICY, GitHubReviews, trusted_policy, parse_policy
from .transaction import JOURNAL, LOCK, commit_files, digest_file, locked, read_bytes


def category(path):
    if path == MANIFEST or path.startswith("docs/workflow/history/") or path in {JOURNAL, LOCK}:
        raise WorkflowError("generated index, transaction state, and audited history are not direct edit targets")
    if path in {"results/ledger.csv", "report/report.docx", "report/report.pdf", "report/source.sha256", "report/parity.sha256"} or path.startswith("results/logs/"):
        raise WorkflowError("runner/generated artifacts cannot be edited by this workflow")
    if path in {"AGENTS.md", "CLAUDE.md", ".codex/AGENTS.md", ".github/copilot-instructions.md", ".cursor/rules/agent-rules.md"}:
        raise WorkflowError("generated instructions must be regenerated from their canonical source")
    if path in {POLICY, "RESEARCH_RULES.md", ".beryl/agent/security-policy.md", ".beryl/agent/synchronization-contract.md"}:
        return "safety"
    if path.startswith(".beryl/agent/"):
        return "instructions"
    if path.startswith(RUN_EVIDENCE + "/"):
        return "research"
    if path.startswith(("docs/", "notes/", "report/sections/")) or path in {"ProjectProposal.md", "references.md", "readingList.md", "report/report.md", "report/report.tex", "solution/PRD.md"}:
        return "research"
    if path.startswith(("workflow/", "tests/", ".github/")) or path in {"README.md", "CONTRIBUTING.md"}:
        return "maintenance"
    raise WorkflowError(f"unknown ownership category for {path}")


def _inputs(root: Path, changes):
    root = root.resolve()
    paths = {POLICY, *changes}
    for prefix in (RECORDS, "docs/workflow/history"):
        directory = safe_path(root, prefix)
        if directory.exists():
            paths.update(p.relative_to(root).as_posix() for p in directory.rglob("*") if p.is_file())
    for path in list(paths):
        if path.endswith(".md") and path.startswith((RECORDS + "/", HISTORY + "/")):
            text = changes.get(path)
            if text is None:
                text = safe_path(root, path).read_text(encoding="utf-8")
            details = parse_record(text, path).metadata["details"]
            for key in ("protocol_ref", "analysis_ref", "evidence_ref"):
                if key in details:
                    paths.add(details[key])
    return {p: digest_file(root, p) for p in sorted(paths)}


def _digest(proposal):
    return sha256(canonical_json({k: v for k, v in proposal.items() if k != "digest"}))


def _diff(root, changes):
    diff = ""
    for path, text in sorted(changes.items()):
        old = read_bytes(root, path)
        old_text = "" if old is None else old.decode("utf-8")
        diff += "".join(difflib.unified_diff(old_text.splitlines(True), text.splitlines(True), fromfile=path + " (before)", tofile=path + " (proposed)"))
    return diff


def propose_change(root: Path, changes: dict[str, str], *, author: str, reason: str,
                   evidence=None, trusted_ref="origin/main", mode="change", reverses=None):
    root = root.resolve()
    if not isinstance(changes, dict) or not changes or not isinstance(author, str) or not author.strip() or not isinstance(reason, str) or not reason.strip():
        raise WorkflowError("nonempty changes, author, and reason required")
    policy, commit, policy_text = trusted_policy(root, trusted_ref)
    current_policy = read_bytes(root, POLICY)
    if current_policy != policy_text.encode():
        raise WorkflowError("working-copy policy differs from trusted Git policy")
    for path, text in changes.items():
        safe_path(root, path)
        category(path)
        if not isinstance(text, str) or len(text.encode()) > 1024 * 1024 or read_bytes(root, path) == text.encode():
            raise WorkflowError("each proposed file must contain a nonempty change below 1 MiB")
        if path.startswith(RUN_EVIDENCE + "/"):
            from .records import read_run_evidence, prepare_run_evidence
            archive = read_run_evidence(root, path, changes)
            prepared = prepare_run_evidence(root, archive["run_id"])
            if prepared["changes"] != {path: text}:
                raise WorkflowError("proposed run evidence must match the existing runner row and log")
    if mode not in {"change", "rollback"}:
        raise WorkflowError("unknown proposal mode")
    evidence = evidence or []
    if not isinstance(evidence, list):
        raise WorkflowError("evidence references must be a list")
    before = validate_records(root)
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"id", "revision"} or (item["id"], item["revision"]) not in before.versions:
            raise WorkflowError("proposal evidence must identify an existing exact record revision")
    validate_change(root, changes, rollback=mode == "rollback")
    proposal = {"schema_version": 1, "author": author, "reason": reason, "evidence": evidence,
                "trusted_base": commit, "policy_sha256": sha256(policy_text), "snapshot": _inputs(root, changes),
                "changes": dict(sorted(changes.items())), "diff": _diff(root, changes), "mode": mode, "reverses": reverses}
    proposal["digest"] = _digest(proposal)
    if len(canonical_json(proposal).encode("utf-8")) > 1024 * 1024:
        raise WorkflowError("proposal exceeds the supported 1 MiB review-content limit")
    validate_proposal(root, proposal)
    return proposal


def _validate_reversal(root, proposal):
    import re
    digest = proposal["reverses"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise WorkflowError("rollback requires an applied proposal digest")
    receipt_path = safe_path(root, f"docs/workflow/history/changes/{digest}.json")
    if not receipt_path.is_file():
        raise WorkflowError("rollback requires an existing applied change receipt")
    receipt = load_json(receipt_path.read_bytes())
    if receipt["proposal"]["digest"] != digest or _digest(receipt["proposal"]) != digest:
        raise WorkflowError("invalid rollback audit receipt")
    restored = set()
    for path, old in receipt["before"].items():
        if path.startswith(RECORDS + "/") and old is not None and parse_record(old, path).metadata["type"] == "decision":
            continue
        if old is None or path not in proposal["changes"]:
            raise WorkflowError("rollback must restore prior files; retire new records separately")
        if digest_file(root, path) != receipt["after_hashes"][path]:
            raise WorkflowError("rollback conflicts with a later edit")
        new = proposal["changes"][path]
        if path.startswith(RECORDS + "/"):
            a, b = parse_record(old, path), parse_record(new, path)
            old_meta, new_meta = dict(a.metadata), dict(b.metadata)
            old_meta.pop("revision")
            new_meta.pop("revision")
            # A fresh approval decision can target the restored higher revision.
            old_meta["links"] = [l for l in old_meta["links"] if l["relation"] != "decision"]
            new_meta["links"] = [l for l in new_meta["links"] if l["relation"] != "decision"]
            if old_meta != new_meta or record_body(old) != record_body(new):
                raise WorkflowError("rollback content must match the retained earlier version")
        elif new != old:
            raise WorkflowError("rollback content must match the retained earlier version")
        restored.add(path)
    for path in proposal["changes"].keys() - restored:
        if not path.startswith(RECORDS + "/") or parse_record(proposal["changes"][path], path).metadata["type"] != "decision":
            raise WorkflowError("additional rollback changes must be supporting decisions")


def validate_proposal(root: Path, proposal: dict):
    fields = {"schema_version", "author", "reason", "evidence", "trusted_base", "policy_sha256", "snapshot", "changes", "diff", "mode", "reverses", "digest"}
    if not isinstance(proposal, dict) or set(proposal) != fields or type(proposal["schema_version"]) is not int or proposal["schema_version"] != 1 or proposal["digest"] != _digest(proposal):
        raise WorkflowError("invalid proposal schema or digest")
    import re
    if any(not isinstance(proposal[key], str) or not re.fullmatch(pattern, proposal[key]) for key, pattern in
           (("trusted_base", r"[0-9a-f]{40,64}"), ("policy_sha256", r"[0-9a-f]{64}"), ("digest", r"[0-9a-f]{64}"))):
        raise WorkflowError("proposal revisions and hashes must be exact digests")
    if proposal["mode"] not in {"change", "rollback"} or not isinstance(proposal["changes"], dict) or not proposal["changes"]:
        raise WorkflowError("invalid proposal mode or changes")
    if not isinstance(proposal["author"], str) or not proposal["author"].strip() or not isinstance(proposal["reason"], str) or not proposal["reason"].strip():
        raise WorkflowError("proposal author and reason required")
    if proposal["mode"] == "rollback":
        _validate_reversal(root, proposal)
    elif proposal["reverses"] is not None:
        raise WorkflowError("ordinary change cannot claim a rollback receipt")
    if proposal["snapshot"] != _inputs(root, proposal["changes"]):
        raise WorkflowError("stale proposal inputs; prepare a new proposal and review")
    if proposal["diff"] != _diff(root, proposal["changes"]):
        raise WorkflowError("proposal diff does not match the exact replacement content")
    for path in proposal["changes"]:
        category(path)
    if POLICY in proposal["changes"]:
        parse_policy(proposal["changes"][POLICY])
    before = validate_records(root)
    if not isinstance(proposal["evidence"], list):
        raise WorkflowError("proposal evidence must be a list")
    for reference in proposal["evidence"]:
        if not isinstance(reference, dict) or set(reference) != {"id", "revision"} or not isinstance(reference["id"], str) or type(reference["revision"]) is not int or (reference["id"], reference["revision"]) not in before.versions:
            raise WorkflowError("invalid proposal evidence revision")
    return validate_change(root, proposal["changes"], rollback=proposal["mode"] == "rollback")


def _groups(root, proposal, policy):
    groups = {}
    before = validate_records(root)
    for path, text in proposal["changes"].items():
        kind = category(path)
        if kind in {"safety", "instructions", "maintenance"}:
            groups["maintainer"] = {n.lower() for n in policy["maintainers"]}
        if kind == "safety" or (kind == "research" and not path.startswith(RECORDS + "/")):
            groups["researcher"] = {n.lower() for n in policy["researchers"]}
        if path.startswith(RECORDS + "/"):
            meta = parse_record(text, path).metadata
            owners = {meta["owner"]}
            if meta["id"] in before.current:
                owners.add(before.current[meta["id"]].metadata["owner"])
            for owner in owners:
                groups[f"owner:{owner}"] = {n.lower() for n in policy["owners"].get(owner, [])}
    return groups


def apply_approved_change(root: Path, proposal: dict, *, pull_number: int, trusted_ref="origin/main", verifier=None):
    root = root.resolve()
    with locked(root):
        if safe_path(root, JOURNAL).exists():
            raise WorkflowError("unfinished transaction; recover before applying a proposal")
        validate_proposal(root, proposal)
        policy, commit, text = trusted_policy(root, trusted_ref)
        if sha256(text) != proposal["policy_sha256"] or read_bytes(root, POLICY) != text.encode():
            raise WorkflowError("trusted policy changed; new review required")
        # Trust is supplied by the integration caller, not by a proposal author.
        from .reviews import git
        git(root, "merge-base", "--is-ancestor", proposal["trusted_base"], commit)
        reviews = (verifier or GitHubReviews()).verify(proposal, policy, _groups(root, proposal, policy), pull_number)
        validate_proposal(root, proposal)
        receipt_path = f"docs/workflow/history/changes/{proposal['digest']}.json"
        if safe_path(root, receipt_path).exists():
            raise WorkflowError("proposal already applied; use a new reviewed change")
        updates = dict(proposal["changes"])
        before = validate_records(root)
        for ident, rec in before.current.items():
            if rec.path in updates:
                archived = f"{HISTORY}/{ident}/{rec.metadata['revision']}.md"
                if safe_path(root, archived).exists():
                    raise WorkflowError("record history already exists; refuse to overwrite it")
                updates[archived] = rec.text
        for path in proposal["changes"]:
            old_content = read_bytes(root, path)
            if old_content is not None and not path.startswith(RECORDS + "/"):
                archived = f"{ARTIFACT_HISTORY}/{sha256(old_content)}.txt"
                if safe_path(root, archived).exists() and read_bytes(root, archived) != old_content:
                    raise WorkflowError("artifact history digest mismatch")
                updates[archived] = old_content.decode("utf-8")
        receipt = {"schema_version": 1, "applied_at": datetime.now(timezone.utc).isoformat(),
                   "proposal": proposal, "trusted_policy_commit": commit, "pull_number": pull_number, "reviews": reviews,
                   "before": {p: None if read_bytes(root, p) is None else read_bytes(root, p).decode("utf-8") for p in proposal["changes"]},
                   "after_hashes": {p: sha256(t) for p, t in proposal["changes"].items()}}
        updates[MANIFEST] = canonical_json(build_manifest(root, updates))
        updates[receipt_path] = canonical_json(receipt)
        commit_files(root, {path: content.encode("utf-8") for path, content in updates.items()})
        return receipt


def propose_rollback(root: Path, digest: str, *, author: str, reason: str, trusted_ref="origin/main"):
    import re
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise WorkflowError("valid applied proposal digest required")
    receipt = load_json(safe_path(root, f"docs/workflow/history/changes/{digest}.json").read_bytes())
    changes = {}
    for path, old in receipt["before"].items():
        if old is None:
            raise WorkflowError("rollback does not delete records; retire newly created records in another proposal")
        if digest_file(root, path) != receipt["after_hashes"][path]:
            raise WorkflowError("rollback conflicts with a later edit; prepare an explicit replacement proposal")
        if path.startswith(RECORDS + "/"):
            original = parse_record(old, path)
            if original.metadata["type"] == "decision":
                continue
            current = parse_record(safe_path(root, path).read_bytes().decode("utf-8"), path)
            meta = dict(original.metadata, revision=current.metadata["revision"] + 1)
            old = encode_record(meta, record_body(old))
        changes[path] = old
    return propose_change(root, changes, author=author, reason=reason, trusted_ref=trusted_ref, mode="rollback", reverses=digest)


def validate_tree_change(root: Path, base: str):
    """Check transitions and append-only history even for hand-edited Git changes.

    This is structural validation; protected-branch review remains external.
    """
    import subprocess
    from .reviews import git
    root = root.resolve()
    commit = git(root, "rev-parse", "--verify", "--end-of-options", base + "^{commit}")
    names = git(root, "ls-tree", "-r", "--name-only", commit).splitlines()
    before_files = {}
    for name in names:
        if name.startswith(("docs/workflow/history/", RUN_EVIDENCE + "/")):
            old = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=root)
            if read_bytes(root, name) != old:
                raise WorkflowError(f"audited history changed or deleted: {name}")
        if name.startswith(RECORDS + "/") and name.endswith(".md"):
            before_files[name] = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=root).decode("utf-8")
    current = validate_records(root)
    for path, text in before_files.items():
        old = parse_record(text, path)
        new = current.current.get(old.metadata["id"])
        if new is None:
            raise WorkflowError(f"current record removed; retire it instead: {path}")
        if new.text != old.text:
            a, b = old.metadata, new.metadata
            if new.path != path or b["type"] != a["type"] or b["created_at"] != a["created_at"] or b["revision"] != a["revision"] + 1:
                raise WorkflowError(f"invalid record identity/revision change: {path}")
            retained = safe_path(root, f"{HISTORY}/{a['id']}/{a['revision']}.md")
            if not retained.is_file() or retained.read_bytes().decode("utf-8") != text:
                raise WorkflowError(f"previous record revision not retained: {path}")
            receipts = list(safe_path(root, "docs/workflow/history/changes").glob("*.json"))
            matching = []
            for receipt_path in receipts:
                receipt = load_json(safe_path(root, receipt_path.relative_to(root).as_posix()).read_bytes())
                if receipt.get("before", {}).get(path) == text and receipt.get("after_hashes", {}).get(path) == sha256(new.text):
                    matching.append(receipt)
            if not matching:
                raise WorkflowError(f"record change has no applied proposal receipt: {path}")
            for receipt in matching:
                proposal = receipt["proposal"]
                if proposal["digest"] != _digest(proposal):
                    raise WorkflowError("invalid audit proposal digest")
                if proposal["mode"] != "rollback" and b["status"] != a["status"] and b["status"] not in TRANSITIONS[a["type"]][a["status"]]:
                    raise WorkflowError(f"invalid state transition: {path}")
    old_ids = {parse_record(text, path).metadata["id"] for path, text in before_files.items()}
    for ident, rec in current.current.items():
        if ident not in old_ids and (rec.metadata["revision"] != 1 or rec.metadata["status"] != INITIAL[rec.metadata["type"]]):
            raise WorkflowError(f"new record skips initial state: {rec.path}")
