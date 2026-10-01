"""Review and transaction behavior against temporary repositories and API fixtures."""
from __future__ import annotations

import base64
import copy
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_workflow_records import record, put, link
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
