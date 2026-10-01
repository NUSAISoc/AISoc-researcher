"""Review and transaction behavior against temporary repositories and API fixtures."""
from __future__ import annotations

import base64
import copy
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_workflow_records import record, put, link, terminal_run_fixture
from workflow.records import WorkflowError, canonical_json, check_manifest, write_manifest, sha256
from workflow.changes import propose_change, validate_proposal, apply_approved_change, propose_rollback, validate_tree_change
from workflow.reviews import GitHubReviews, RemoteNotFound
from workflow.transaction import recover


class ReviewedChangesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = "docs/workflow/records/E1.md"
        self.old = record()
        put(self.root, self.path, self.old)
        put(self.root, "docs/workflow/records/.gitkeep", "")
        put(self.root, "docs/workflow/history/records/.gitkeep", "")
        policy = {"schema_version": 1, "repository": "example/research", "researchers": ["reviewer"],
                  "maintainers": ["maintainer"], "owners": {"researcher": ["reviewer"]}}
        put(self.root, "workflow/policy.json", canonical_json(policy))
        write_manifest(self.root)
        for args in (("init", "-q"), ("config", "user.name", "Fixture"), ("config", "user.email", "fixture@example.invalid"), ("add", "."), ("commit", "-qm", "Fixture base")):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        self.base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        self.proposal = propose_change(self.root, {self.path: record(status="reviewed", revision=2)}, author="test-agent", reason="Review fixture source", trusted_ref="HEAD")
        self.head = "a" * 40
        self.reviews = [{"id": 1, "user": {"login": "reviewer", "type": "User"}, "state": "APPROVED",
                         "commit_id": self.head, "submitted_at": "2026-10-01T00:00:00Z", "html_url": "https://github.com/example/research/pull/7#pullrequestreview-1"}]

    def verifier(self, proposal=None):
        proposal = proposal or self.proposal
        sources = {p: (self.root / p).read_bytes() if (self.root / p).exists() else None for p in proposal["snapshot"]}

        def fetch(endpoint):
            if endpoint.endswith("/pulls/7"):
                return {"state": "open", "draft": False, "user": {"login": "test-agent"},
                        "base": {"repo": {"full_name": "example/research"}},
                        "head": {"sha": self.head, "repo": {"full_name": "example/research"}}}
            if "/reviews?" in endpoint:
                return self.reviews
            if "/contents/" in endpoint:
                from urllib.parse import unquote
                path = unquote(endpoint.split("/contents/", 1)[1].split("?", 1)[0])
                if path == f"docs/workflow/proposals/{proposal['digest']}.json":
                    content = canonical_json(proposal).encode()
                else:
                    content = sources.get(path)
                    if content is None:
                        raise RemoteNotFound("fixture HTTP 404")
                return {"encoding": "base64", "content": base64.b64encode(content).decode()}
            raise AssertionError(endpoint)

        return GitHubReviews(fetch=fetch)

    def apply(self, proposal=None, verifier=None):
        return apply_approved_change(self.root, proposal or self.proposal, pull_number=7,
                                     trusted_ref="HEAD", verifier=verifier or self.verifier(proposal))

    def test_proposal_is_readable_and_does_not_mutate_records(self):
        self.assertEqual((self.root / self.path).read_text(), self.old)
        self.assertIn("---", self.proposal["diff"])
        self.assertIn("Review fixture source", self.proposal["reason"])
        validate_proposal(self.root, self.proposal)

    def test_verified_change_preserves_history_and_regenerates_manifest(self):
        receipt = self.apply()
        self.assertEqual(json.loads((self.root / "docs/workflow/manifest.json").read_text())["records"][0]["revision"], 2)
        self.assertEqual((self.root / "docs/workflow/history/records/E1/1.md").read_text(), self.old)
        self.assertEqual(receipt["reviews"][0]["reviewer"], "reviewer")
        check_manifest(self.root)
        validate_tree_change(self.root, self.base)

    def test_terminal_runs_survive_checkout_and_do_not_block_unrelated_apply(self):
        for status in ("completed", "failed"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as checkout:
                terminal_run_fixture(self.root, status)
                put(self.root, ".gitignore", "results/logs/*.jsonl\n")
                write_manifest(self.root)
                # Promote only the reviewed archive. The tracked runtime ledger stays empty.
                ledger = self.root / "results/ledger.csv"
                runtime_ledger = ledger.read_bytes()
                ledger.write_text("run_id,status,synthetic,config_hash\n")
                for args in (("add", "."), ("commit", "-qm", "Test-only reviewed run archive")):
                    subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
                ledger.write_bytes(runtime_ledger)
                subprocess.run(["git", "clone", "-q", str(self.root), checkout], check=True, capture_output=True)
                source_root, self.root = self.root, Path(checkout)
                try:
                    self.assertFalse((self.root / "results/logs/fixture-run.jsonl").exists())
                    check_manifest(self.root)
                    proposal = propose_change(self.root, {self.path: record(status="admitted", revision=2) + "Reviewed clarification.\n"},
                                              author="test-agent", reason="Unrelated evidence edit", trusted_ref="HEAD")
                    self.assertNotIn("results/ledger.csv", proposal["snapshot"])
                    self.assertNotIn("results/logs/fixture-run.jsonl", proposal["snapshot"])
                    self.apply(proposal)
                    check_manifest(self.root)
                    validate_tree_change(self.root, "HEAD")
                    # Historical terminal records must also resolve the archive.
                    run = self.root / "docs/workflow/records/R1.md"
                    original = run.read_text()
                    put(self.root, "docs/workflow/history/records/R1/1.md", original)
                    meta = json.loads(original.split("```json\n", 1)[1].split("\n```", 1)[0])
                    meta.update(revision=2, links=[link("campaign", "C1"), link("decision", "D2")])
                    from workflow.records import encode_record
                    put(self.root, "docs/workflow/records/D2.md", record("decision", "D2", "approved", links=[link("target", "R1", 2)]))
                    put(self.root, "docs/workflow/records/R1.md", encode_record(meta, "Historical fixture check.\n"))
                    write_manifest(self.root)
                    check_manifest(self.root)
                finally:
                    self.root = source_root

    def test_terminal_transition_applies_archive_in_same_reviewed_change(self):
        from workflow.records import prepare_run_evidence
        prepared = terminal_run_fixture(self.root)
        archive_path = prepared["details"]["evidence_ref"]
        (self.root / archive_path).unlink()
        rpath, dpath = "docs/workflow/records/R1.md", "docs/workflow/records/D2.md"
        put(self.root, rpath, record("run", "R1", "running", links=[link("campaign", "C1"), link("decision", "D1")]))
        put(self.root, dpath, record("decision", "D2", links=[link("target", "R1")]))
        write_manifest(self.root)
        changes = dict(prepared["changes"])
        changes[rpath] = record("run", "R1", "failed", revision=2, links=[link("campaign", "C1"), link("decision", "D2", 2)], details=prepared["details"])
        changes[dpath] = record("decision", "D2", "approved", revision=2, links=[link("target", "R1", 2)])
        proposal = propose_change(self.root, changes, author="test-agent", reason="Retain test-only runner evidence", trusted_ref="HEAD")
        self.assertIsNone(proposal["snapshot"][archive_path])
        self.assertFalse((self.root / archive_path).exists())
        self.apply(proposal)
        self.assertEqual((self.root / archive_path).read_text(), prepared["changes"][archive_path])
        check_manifest(self.root)
        with self.assertRaisesRegex(WorkflowError, "immutable"):
            from workflow.records import validate_change
            validate_change(self.root, prepared["changes"])

    def test_archive_preparation_and_cli_refuse_invented_or_changed_runner_evidence(self):
        from workflow.__main__ import main
        from workflow.records import canonical_json, sha256
        prepared = terminal_run_fixture(self.root)
        archive_path = prepared["details"]["evidence_ref"]
        (self.root / archive_path).unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--root", str(self.root), "run-reference", "--run-id", "fixture-run", "--archive"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), prepared)
        self.assertFalse((self.root / archive_path).exists())
        archive = json.loads(prepared["changes"][archive_path])
        archive["log"] = '{"invented":true}\n'
        text = canonical_json(archive)
        fake_path = f"results/evidence/fixture-run/{sha256(text)}.json"
        with self.assertRaisesRegex(WorkflowError, "existing runner"):
            propose_change(self.root, {fake_path: text}, author="test-agent", reason="Fixture tamper", trusted_ref="HEAD")

    def test_hypothesis_and_decision_are_approved_together_and_reversible(self):
        put(self.root, self.path, record(status="admitted"))
        hpath = "docs/workflow/records/H1.md"
        dpath = "docs/workflow/records/D1.md"
        put(self.root, hpath, record("hypothesis", "H1", links=[link("evidence", "E1")]))
        put(self.root, dpath, record("decision", "D1", links=[link("target", "H1")]))
        write_manifest(self.root)
        changes = {
            hpath: record("hypothesis", "H1", "approved", revision=2, links=[link("evidence", "E1"), link("decision", "D1", 2)]),
            dpath: record("decision", "D1", "approved", revision=2, links=[link("target", "H1", 2)]),
        }
        proposal = propose_change(self.root, changes, author="test-agent", reason="Approve fixture hypothesis", trusted_ref="HEAD")
        self.apply(proposal)
        check_manifest(self.root)
        reversal = propose_rollback(self.root, proposal["digest"], author="test-agent", reason="Undo fixture approval", trusted_ref="HEAD")
        self.assertNotIn(dpath, reversal["changes"])
        self.apply(reversal)
        self.assertIn('"status": "draft"', (self.root / hpath).read_text())
        self.assertIn('"status": "approved"', (self.root / dpath).read_text())
        check_manifest(self.root)

    def test_safety_policy_edit_requires_researcher_and_maintainer(self):
        path = "RESEARCH_RULES.md"
        put(self.root, path, "Test-only rules\n")
        proposal = propose_change(self.root, {path: "Reviewed test-only rules\n"}, author="test-agent", reason="Fixture policy change", trusted_ref="HEAD")
        with self.assertRaisesRegex(WorkflowError, "maintainer"):
            self.apply(proposal)
        self.reviews.append(dict(self.reviews[0], id=2, user={"login": "maintainer", "type": "User"}))
        receipt = self.apply(proposal)
        self.assertEqual({r["role"] for r in receipt["reviews"]}, {"maintainer", "researcher"})

    def test_protocol_change_preserves_the_old_approved_artifact(self):
        put(self.root, self.path, record(status="admitted"))
        protocol = "docs/protocol.md"
        put(self.root, protocol, "Test-only protocol\n")
        put(self.root, "docs/workflow/records/H1.md", record("hypothesis", "H1", "approved", links=[link("evidence", "E1"), link("decision", "D1")]))
        cpath = "docs/workflow/records/C1.md"
        put(self.root, cpath, record("campaign", "C1", "active", links=[link("hypothesis", "H1"), link("decision", "D1")]))
        put(self.root, "docs/workflow/records/D1.md", record("decision", "D1", "approved", links=[link("target", "H1"), link("target", "C1")]))
        dpath = "docs/workflow/records/D2.md"
        put(self.root, dpath, record("decision", "D2", links=[link("target", "C1")]))
        write_manifest(self.root)
        new_protocol = "Revised test-only protocol\n"
        changes = {
            protocol: new_protocol,
            cpath: record("campaign", "C1", "active", revision=2, links=[link("hypothesis", "H1"), link("decision", "D2", 2)],
                          details={"protocol_ref": protocol, "protocol_sha256": sha256(new_protocol), "stopping_rules": "Stop after fixture execution"}),
            dpath: record("decision", "D2", "approved", revision=2, links=[link("target", "C1", 2)]),
        }
        proposal = propose_change(self.root, changes, author="test-agent", reason="Revise fixture protocol", trusted_ref="HEAD")
        self.apply(proposal)
        archived = self.root / f"docs/workflow/history/artifacts/{sha256('Test-only protocol' + chr(10))}.txt"
        self.assertEqual(archived.read_text(), "Test-only protocol\n")
        check_manifest(self.root)

    def test_hand_edited_record_cannot_skip_retained_history(self):
        put(self.root, self.path, record(status="reviewed", revision=2))
        with self.assertRaisesRegex(WorkflowError, "retained"):
            write_manifest(self.root)
        with self.assertRaisesRegex(WorkflowError, "retained"):
            validate_tree_change(self.root, self.base)

    def test_cli_proposal_validation_application_and_inspection(self):
        from workflow.__main__ import main
        change_set = self.root / "changes.json"
        change_set.write_text(canonical_json(self.proposal["changes"]))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--root", str(self.root), "propose", "--changes", str(change_set),
                           "--author", "test-agent", "--reason", "Review fixture source", "--trusted-base", "HEAD", "--save"])
        self.assertEqual(result, 0)
        self.assertIn("pending review", output.getvalue())
        self.assertEqual((self.root / self.path).read_text(), self.old)
        saved = self.root / f"docs/workflow/proposals/{self.proposal['digest']}.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--root", str(self.root), "validate", "--proposal", str(saved)]), 0)
            with mock.patch("workflow.changes.GitHubReviews", return_value=self.verifier()):
                self.assertEqual(main(["--root", str(self.root), "apply", "--proposal", str(saved), "--pull-number", "7", "--trusted-base", "HEAD"]), 0)
            self.assertEqual(main(["--root", str(self.root), "check", "--base", self.base]), 0)

    def test_no_approval_wrong_commit_bot_and_self_approval_fail_closed(self):
        variants = [[], [dict(self.reviews[0], state="COMMENTED")], [dict(self.reviews[0], commit_id="b" * 40)],
                    [dict(self.reviews[0], user={"login": "reviewer", "type": "Bot"})],
                    [dict(self.reviews[0], user={"login": "test-agent", "type": "User"})]]
        for reviews in variants:
            with self.subTest(reviews=reviews):
                self.reviews = reviews
                with self.assertRaises(WorkflowError):
                    self.apply()
                self.assertEqual((self.root / self.path).read_text(), self.old)

    def test_dismissed_or_later_changes_requested_revokes_approval(self):
        for state in ("DISMISSED", "CHANGES_REQUESTED"):
            with self.subTest(state=state):
                self.reviews = [dict(self.reviews[0], id=1, state="APPROVED"), dict(self.reviews[0], id=2, state=state)]
                with self.assertRaises(WorkflowError):
                    self.apply()

    def test_comment_does_not_erase_valid_approval(self):
        self.reviews.append(dict(self.reviews[0], id=2, state="COMMENTED"))
        self.apply()

    def test_changed_remote_proposal_is_not_authorized(self):
        remote = copy.deepcopy(self.proposal)
        remote["reason"] = "Different reviewed proposal"
        with self.assertRaisesRegex(WorkflowError, "reviewed proposal"):
            self.apply(verifier=self.verifier(remote))

    def test_approval_must_cover_the_same_evidence_snapshot(self):
        original = self.verifier().fetch

        def different_source(endpoint):
            if "/contents/docs/workflow/records/E1.md?" in endpoint:
                return {"encoding": "base64", "content": base64.b64encode(b"Different reviewed evidence").decode()}
            return original(endpoint)

        with self.assertRaisesRegex(WorkflowError, "source snapshot"):
            self.apply(verifier=GitHubReviews(fetch=different_source))

    def test_changed_head_during_verification_requires_new_review(self):
        original = self.verifier().fetch
        reads = 0

        def changed_head(endpoint):
            nonlocal reads
            response = original(endpoint)
            if endpoint.endswith("/pulls/7"):
                reads += 1
                if reads == 2:
                    response["head"]["sha"] = "b" * 40
            return response

        with self.assertRaisesRegex(WorkflowError, "changed during"):
            self.apply(verifier=GitHubReviews(fetch=changed_head))

    def test_stale_file_new_record_or_policy_edit_requires_new_review(self):
        for path, text in ((self.path, self.old + "Concurrent edit\n"),
                           ("docs/workflow/records/E2.md", record(ident="E2")),
                           ("workflow/policy.json", "{}\n")):
            with self.subTest(path=path):
                put(self.root, path, text)
                with self.assertRaises(WorkflowError):
                    self.apply()
                if path == self.path:
                    put(self.root, path, self.old)
                elif path.endswith("E2.md"):
                    (self.root / path).unlink()

    def test_network_failure_cannot_authorize_application(self):
        def unavailable(endpoint):
            raise WorkflowError("review verification unavailable")
        with self.assertRaisesRegex(WorkflowError, "unavailable"):
            self.apply(verifier=GitHubReviews(fetch=unavailable))
        self.assertEqual((self.root / self.path).read_text(), self.old)

    def test_proposal_tampering_and_generated_or_audited_edits_fail(self):
        tampered = copy.deepcopy(self.proposal)
        tampered["changes"][self.path] = self.old
        with self.assertRaisesRegex(WorkflowError, "digest"):
            validate_proposal(self.root, tampered)
        for path in ("docs/workflow/manifest.json", "results/ledger.csv", "docs/workflow/history/records/E1/1.md", "../outside.md", ".git/config"):
            with self.subTest(path=path):
                with self.assertRaises(WorkflowError):
                    propose_change(self.root, {path: "unapproved"}, author="agent", reason="fixture", trusted_ref="HEAD")

    def test_recomputed_digest_cannot_disguise_the_diff(self):
        from workflow.records import sha256
        tampered = copy.deepcopy(self.proposal)
        tampered["diff"] = "Nothing important changed."
        tampered["digest"] = sha256(canonical_json({k: v for k, v in tampered.items() if k != "digest"}))
        with self.assertRaisesRegex(WorkflowError, "diff"):
            validate_proposal(self.root, tampered)

    def test_reviewed_rollback_creates_new_revision_and_receipt(self):
        self.apply()
        reversal = propose_rollback(self.root, self.proposal["digest"], author="test-agent", reason="Restore fixture content", trusted_ref="HEAD")
        self.assertEqual(reversal["mode"], "rollback")
        self.assertIn('"revision": 3', reversal["changes"][self.path])
        self.apply(reversal)
        self.assertEqual((self.root / "docs/workflow/history/records/E1/2.md").read_text(), self.proposal["changes"][self.path])
        check_manifest(self.root)
        validate_tree_change(self.root, self.base)

    def test_base_check_walks_each_applied_revision(self):
        self.apply()
        next_proposal = propose_change(self.root, {self.path: record(status="excluded", revision=3)},
                                      author="test-agent", reason="Exclude fixture", trusted_ref="HEAD")
        self.apply(next_proposal)
        validate_tree_change(self.root, self.base)
        for proposal in (self.proposal, next_proposal):
            receipt = self.root / f"docs/workflow/history/changes/{proposal['digest']}.json"
            saved = receipt.read_bytes()
            receipt.unlink()
            with self.assertRaisesRegex(WorkflowError, "receipt"):
                validate_tree_change(self.root, self.base)
            receipt.write_bytes(saved)
        history = self.root / "docs/workflow/history/records/E1/2.md"
        history.unlink()
        with self.assertRaisesRegex(WorkflowError, "retained"):
            validate_tree_change(self.root, self.base)

    def test_new_record_can_advance_after_creation_in_same_branch(self):
        path = "docs/workflow/records/E2.md"
        creation = propose_change(self.root, {path: record(ident="E2")}, author="test-agent", reason="Create fixture", trusted_ref="HEAD")
        self.apply(creation)
        review = propose_change(self.root, {path: record(ident="E2", status="reviewed", revision=2)},
                                author="test-agent", reason="Review new fixture", trusted_ref="HEAD")
        self.apply(review)
        validate_tree_change(self.root, self.base)

    def test_base_check_rejects_invalid_intermediate_transition(self):
        # Two individually valid record files can still form an invalid lifecycle step.
        from workflow.changes import _digest
        from workflow.records import sha256
        self.apply()
        next_proposal = propose_change(self.root, {self.path: record(status="excluded", revision=3)},
                                      author="test-agent", reason="Exclude fixture", trusted_ref="HEAD")
        self.apply(next_proposal)
        revised = record(status="admitted", revision=3)
        put(self.root, self.path, revised)
        receipt_path = self.root / f"docs/workflow/history/changes/{next_proposal['digest']}.json"
        receipt = json.loads(receipt_path.read_bytes())
        receipt["proposal"]["changes"][self.path] = revised
        receipt["after_hashes"][self.path] = sha256(revised)
        # Make the first step invalid instead: captured -> excluded.
        intermediate = record(status="excluded", revision=2)
        put(self.root, "docs/workflow/history/records/E1/2.md", intermediate)
        first_path = self.root / f"docs/workflow/history/changes/{self.proposal['digest']}.json"
        first = json.loads(first_path.read_bytes())
        first["proposal"]["changes"][self.path] = intermediate
        first["after_hashes"][self.path] = sha256(intermediate)
        receipt["before"][self.path] = intermediate
        receipt["proposal"]["snapshot"][self.path] = sha256(intermediate)
        for path, item in ((first_path, first), (receipt_path, receipt)):
            path.unlink()
            item["proposal"]["digest"] = _digest(item["proposal"])
            put(self.root, f"docs/workflow/history/changes/{item['proposal']['digest']}.json", canonical_json(item))
        write_manifest(self.root)
        with self.assertRaisesRegex(WorkflowError, "state transition"):
            validate_tree_change(self.root, self.base)

    def test_base_check_binds_receipt_name_and_requires_real_reversal_target(self):
        from workflow.changes import _digest
        self.apply()
        receipt_path = self.root / f"docs/workflow/history/changes/{self.proposal['digest']}.json"
        renamed = receipt_path.with_name("0" * 64 + ".json")
        receipt_path.rename(renamed)
        with self.assertRaisesRegex(WorkflowError, "filename"):
            validate_tree_change(self.root, self.base)
        renamed.rename(receipt_path)
        receipt = json.loads(receipt_path.read_bytes())
        receipt_path.unlink()
        receipt["proposal"].update(mode="rollback", reverses="0" * 64)
        receipt["proposal"]["digest"] = _digest(receipt["proposal"])
        put(self.root, f"docs/workflow/history/changes/{receipt['proposal']['digest']}.json", canonical_json(receipt))
        with self.assertRaisesRegex(WorkflowError, "rollback audit receipt is missing"):
            validate_tree_change(self.root, self.base)

    def test_interruption_leaves_recoverable_journal(self):
        from workflow import transaction
        original = transaction.replace_file
        calls = 0

        def interrupted(path, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise SystemExit("fixture interruption")
            return original(path, content)

        with mock.patch.object(transaction, "replace_file", side_effect=interrupted):
            with self.assertRaises(SystemExit):
                self.apply()
        self.assertTrue((self.root / "docs/workflow/.transaction.json").exists())
        recover(self.root)
        self.assertEqual((self.root / self.path).read_text(), self.old)
        check_manifest(self.root)
        self.assertFalse((self.root / "docs/workflow/.transaction.json").exists())

    def test_killed_approval_verification_recovers_lock_without_journal(self):
        put(self.root, "pending.json", canonical_json(self.proposal))
        script = """
import sys
from pathlib import Path
from workflow.changes import apply_approved_change
from workflow.records import load_json
root = Path(sys.argv[1])
class BlockingReview:
    def verify(self, *args):
        print('verifying', flush=True)
        sys.stdin.read()
apply_approved_change(root, load_json((root / 'pending.json').read_bytes()),
                      pull_number=7, trusted_ref='HEAD', verifier=BlockingReview())
"""
        with subprocess.Popen([sys.executable, "-c", script, str(self.root)], cwd=Path(__file__).resolve().parents[1],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as child:
            try:
                self.assertEqual(child.stdout.readline().strip(), "verifying")
                self.assertTrue((self.root / "docs/workflow/.lock").exists())
                self.assertFalse((self.root / "docs/workflow/.transaction.json").exists())
                with self.assertRaisesRegex(WorkflowError, "lock"):
                    write_manifest(self.root)
                child.kill()
                child.communicate(timeout=5)
                self.assertNotEqual(child.returncode, 0)
                self.assertTrue((self.root / "docs/workflow/.lock").exists())
                self.assertEqual(recover(self.root), "lock-cleared")
                self.assertFalse((self.root / "docs/workflow/.lock").exists())
                self.assertEqual((self.root / self.path).read_text(), self.old)
                write_manifest(self.root)
                self.apply()
                check_manifest(self.root)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=5)

    def test_recovery_preserves_live_and_uncertain_owner_locks_without_journal(self):
        path = self.root / "docs/workflow/.lock"
        for content, message in ((str(os.getpid()), "still running"), ("invalid", "cannot establish"), ("0", "cannot establish")):
            with self.subTest(content=content):
                put(self.root, "docs/workflow/.lock", content)
                with self.assertRaisesRegex(WorkflowError, message):
                    recover(self.root)
                self.assertEqual(path.read_text(), content)
        put(self.root, "docs/workflow/.lock", str(os.getpid()))
        with mock.patch("workflow.transaction.os.kill", side_effect=PermissionError):
            with self.assertRaisesRegex(WorkflowError, "cannot establish"):
                recover(self.root)
        self.assertTrue(path.exists())
        path.unlink()
        with self.assertRaisesRegex(WorkflowError, "no transaction"):
            recover(self.root)

    def test_cli_reports_dead_lock_recovery_without_claiming_recovered_writes(self):
        from workflow.__main__ import main
        put(self.root, "docs/workflow/.lock", "123456789")
        output = io.StringIO()
        with mock.patch("workflow.transaction.os.kill", side_effect=ProcessLookupError), contextlib.redirect_stdout(output):
            result = main(["--root", str(self.root), "recover"])
        self.assertEqual(result, 0)
        self.assertIn("abandoned lock cleared; no transaction writes", output.getvalue())
        self.assertFalse((self.root / "docs/workflow/.lock").exists())
        self.assertEqual((self.root / self.path).read_text(), self.old)

    def test_abrupt_exit_with_journal_recovers_both_writes_and_lock(self):
        script = """
import os, sys
from pathlib import Path
from workflow import transaction
root = Path(sys.argv[1])
original = transaction.replace_file
def interrupted(path, content):
    original(path, content)
    if path.name == 'E1.md':
        os._exit(23)
transaction.replace_file = interrupted
with transaction.locked(root):
    transaction.commit_files(root, {'docs/workflow/records/E1.md': b'Interrupted fixture write'})
"""
        child = subprocess.run([sys.executable, "-c", script, str(self.root)], cwd=Path(__file__).resolve().parents[1],
                               capture_output=True, timeout=10)
        self.assertEqual(child.returncode, 23)
        self.assertTrue((self.root / "docs/workflow/.lock").exists())
        self.assertTrue((self.root / "docs/workflow/.transaction.json").exists())
        recover(self.root)
        self.assertEqual((self.root / self.path).read_text(), self.old)
        self.assertFalse((self.root / "docs/workflow/.lock").exists())
        self.assertFalse((self.root / "docs/workflow/.transaction.json").exists())
        check_manifest(self.root)

    def test_recovery_refuses_to_overwrite_a_concurrent_edit(self):
        from workflow import transaction
        original = transaction.replace_file

        def interrupted(path, content):
            if path.name == ".transaction.json":
                return original(path, content)
            raise SystemExit("fixture interruption")

        with mock.patch.object(transaction, "replace_file", side_effect=interrupted):
            with self.assertRaises(SystemExit):
                self.apply()
        put(self.root, self.path, "Unrelated human edit\n")
        with self.assertRaisesRegex(WorkflowError, "conflict"):
            recover(self.root)
        self.assertEqual((self.root / self.path).read_text(), "Unrelated human edit\n")

    def test_policy_comes_from_trusted_git_base_not_working_copy(self):
        with self.assertRaises(WorkflowError):
            self.apply(verifier=GitHubReviews(fetch=lambda endpoint: {}))
        policy = json.loads((self.root / "workflow/policy.json").read_text())
        policy["owners"]["researcher"] = ["test-agent"]
        put(self.root, "workflow/policy.json", canonical_json(policy))
        with self.assertRaises(WorkflowError):
            propose_change(self.root, {self.path: record(status="reviewed", revision=2)}, author="agent", reason="fixture", trusted_ref="HEAD")


if __name__ == "__main__":
    unittest.main()
