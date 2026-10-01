"""Lifecycle checks use disposable files, never the study's results."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from workflow.records import (
    WorkflowError, encode_record, build_manifest, check_manifest,
    validate_records, validate_change, write_manifest,
)


def record(kind="evidence", ident="E1", status=None, revision=1, links=None, **extra):
    details = {
        "evidence": {"source": "test-only source", "locator": "fixture", "reading_depth": "artifact", "limitations": "Not study evidence"},
        "hypothesis": {"statement": "Test-only proposition"},
        "decision": {"action": "approve test change", "reason": "Fixture review"},
        "campaign": {"protocol_ref": "docs/protocol.md", "stopping_rules": "Stop after fixture execution"},
        "run": {},
        "evaluation": {"analysis_ref": "test-only analysis", "conclusion": "inconclusive"},
        "claim": {"statement": "Test-only claim"},
        "gap": {"description": "Test-only gap"},
        "opportunity": {"description": "Test-only opportunity"},
    }[kind]
    initial = {"evidence": "captured", "hypothesis": "draft", "gap": "identified", "run": "planned", "evaluation": "draft"}
    meta = dict(id=ident, type=kind, status=status or initial.get(kind, "proposed"), owner="researcher", revision=revision,
                created_at="2026-10-01T00:00:00Z", links=links or [], details=details)
    meta.update(extra)
    return encode_record(meta, "# Test fixture\n\nNot a research result.\n")


def link(relation, ident, revision=1):
    return {"relation": relation, "id": ident, "revision": revision}


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class RecordChecksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = "docs/workflow/records/E1.md"
        put(self.root, self.path, record())

    def test_manifest_is_deterministic_and_detects_body_edits(self):
        first = build_manifest(self.root)
        self.assertEqual(first, build_manifest(self.root))
        self.assertEqual(first["records"][0]["id"], "E1")
        write_manifest(self.root)
        check_manifest(self.root)
        put(self.root, self.path, record() + "Changed fixture body.\n")
        with self.assertRaisesRegex(WorkflowError, "manifest"):
            check_manifest(self.root)

    def test_empty_tree_has_no_fabricated_records(self):
        (self.root / self.path).unlink()
        self.assertEqual(build_manifest(self.root), {"schema_version": 1, "records": []})

    def test_duplicate_id_and_boolean_revision_are_rejected(self):
        put(self.root, "docs/workflow/records/duplicate.md", record())
        with self.assertRaisesRegex(WorkflowError, "duplicate"):
            validate_records(self.root)
        (self.root / "docs/workflow/records/duplicate.md").unlink()
        put(self.root, self.path, record(revision=True))
        with self.assertRaisesRegex(WorkflowError, "revision"):
            validate_records(self.root)

    def test_missing_or_wrong_revision_link_is_rejected(self):
        hpath = "docs/workflow/records/H1.md"
        put(self.root, hpath, record("hypothesis", "H1", links=[link("evidence", "E1", 2)]))
        with self.assertRaisesRegex(WorkflowError, "missing revision"):
            validate_records(self.root)
        put(self.root, hpath, record("hypothesis", "H1", links=[link("evidence", "MISSING")]))
        with self.assertRaisesRegex(WorkflowError, "missing revision"):
            validate_records(self.root)

    def test_historical_links_survive_current_record_revision(self):
        put(self.root, "docs/workflow/history/records/E1/1.md", record())
        put(self.root, self.path, record(status="reviewed", revision=2))
        put(self.root, "docs/workflow/records/H1.md", record("hypothesis", "H1", links=[link("evidence", "E1")]))
        self.assertEqual(len(validate_records(self.root).current), 2)

    def test_approval_decision_must_target_exact_hypothesis_revision(self):
        put(self.root, self.path, record(status="admitted"))
        put(self.root, "docs/workflow/records/H1.md", record("hypothesis", "H1", "approved",
            links=[link("evidence", "E1"), link("decision", "D1")]))
        put(self.root, "docs/workflow/records/D1.md", record("decision", "D1", "approved",
            links=[link("target", "E1")]))
        with self.assertRaisesRegex(WorkflowError, "target"):
            validate_records(self.root)
        put(self.root, "docs/workflow/records/D1.md", record("decision", "D1", "approved",
            links=[link("target", "H1")]))
        validate_records(self.root)

    def test_state_skip_revision_reuse_and_identity_change_fail(self):
        for text in (record(status="admitted", revision=2), record(status="reviewed"), record(ident="E2", revision=2)):
            with self.subTest(text=text):
                with self.assertRaises(WorkflowError):
                    validate_change(self.root, {self.path: text})
        validate_change(self.root, {self.path: record(status="reviewed", revision=2)})
        self.assertEqual((self.root / self.path).read_text(), record())

    def test_new_record_must_start_at_initial_state(self):
        with self.assertRaisesRegex(WorkflowError, "initial"):
            validate_change(self.root, {"docs/workflow/records/E2.md": record(ident="E2", status="admitted")})

    def test_created_at_cannot_change_and_unknown_status_fails(self):
        with self.assertRaisesRegex(WorkflowError, "created_at"):
            validate_change(self.root, {self.path: record(status="reviewed", revision=2, created_at="2026-10-02T00:00:00Z")})
        put(self.root, self.path, record(status="imaginary"))
        with self.assertRaisesRegex(WorkflowError, "status"):
            validate_records(self.root)

    def test_retirement_is_separate_from_execution_status(self):
        put(self.root, "docs/workflow/records/D1.md", record("decision", "D1", "approved", links=[link("target", "E1")]))
        put(self.root, self.path, record(retirement={"reason": "Fixture no longer active", "decision": link("decision", "D1")}))
        row = build_manifest(self.root)["records"][1]
        self.assertEqual(row["status"], "captured")
        self.assertFalse(row["active"])

    def test_symlink_and_bad_metadata_are_rejected(self):
        (self.root / "docs/workflow/records/alias.md").symlink_to(self.root / self.path)
        with self.assertRaisesRegex(WorkflowError, "symlink"):
            validate_records(self.root)
        (self.root / "docs/workflow/records/alias.md").unlink()
        put(self.root, self.path, "# No metadata\n")
        with self.assertRaisesRegex(WorkflowError, "metadata"):
            validate_records(self.root)

    def test_terminal_run_requires_exact_ledger_and_log(self):
        put(self.root, self.path, record(status="admitted"))
        put(self.root, "docs/protocol.md", "Test-only protocol\n")
        put(self.root, "docs/workflow/records/H1.md", record("hypothesis", "H1", "approved", links=[link("evidence", "E1"), link("decision", "D1")]))
        put(self.root, "docs/workflow/records/C1.md", record("campaign", "C1", "active", links=[link("hypothesis", "H1"), link("decision", "D1")]))
        put(self.root, "docs/workflow/records/R1.md", record("run", "R1", "failed", links=[link("campaign", "C1"), link("decision", "D1")],
            details={"run_id": "fixture-run", "ledger_ref": "results/ledger.csv", "log_ref": "results/logs/fixture-run.jsonl"}))
        put(self.root, "docs/workflow/records/D1.md", record("decision", "D1", "approved", links=[link("target", "H1"), link("target", "C1"), link("target", "R1")]))
        with self.assertRaisesRegex(WorkflowError, "ledger"):
            validate_records(self.root)
        put(self.root, "results/ledger.csv", "run_id,status,synthetic\nfixture-run,error,true\n")
        put(self.root, "results/logs/fixture-run.jsonl", json.dumps({"status": "error", "synthetic": True}) + "\n")
        validate_records(self.root)
        put(self.root, "results/ledger.csv", "run_id,status,synthetic\nfixture-run,ok,true\n")
        with self.assertRaisesRegex(WorkflowError, "ledger status"):
            validate_records(self.root)


if __name__ == "__main__":
    unittest.main()
