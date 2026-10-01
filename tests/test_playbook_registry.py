"""CI gate for the community research-playbook registry (issue #10).

Validates every committed entry, confirms registry.json matches a fresh
rebuild (immutability + append-only), and pins the malformed-input rules
from playbooks/SCHEMA.md. Stdlib only; auto-discovered by
`python3 -m unittest discover -s tests -t .`.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "playbook_validate", REPO_ROOT / "playbooks" / "validate.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

VALID = """---
id: {id}
version: {ver}
title: Sample
evidence_status: {status}
lifecycle_stages: {stages}
compatibility: ">=0.1.0"
authors: ["Jane Doe <jane@example.org>"]
license: CC-BY-4.0
citations: {cites}
publisher: ""
key_id: ""
signature: ""
---

# Sample
## Purpose
x
## When to use (applicability conditions)
x
## Inputs
x
## Procedure
x
## Expected artifacts
x
## Failure modes
x
## Evidence and validation status
x
## Limitations
x
## Compatibility
x
## Citations
x
"""


def _write(root: Path, id_="sample-play", ver="1.0.0", status="emerging",
           stages="[]", cites='["A (2020). T. V. DOI."]', fname=None):
    d = root / "playbooks" / "entries" / id_
    d.mkdir(parents=True, exist_ok=True)
    p = d / (fname or f"{ver}.md")
    p.write_text(VALID.format(id=id_, ver=ver, status=status, stages=stages, cites=cites),
                 encoding="utf-8")
    return p


class CommittedRegistryTest(unittest.TestCase):
    def test_all_entries_valid(self):
        stems = V.docs_stems(REPO_ROOT)
        for path in V.discover_entries(REPO_ROOT):
            with self.subTest(entry=path.name):
                self.assertEqual(V.validate_entry(path, stems), [])

    def test_index_matches_rebuild(self):
        self.assertEqual(V.check_index(REPO_ROOT), [])

    def test_at_least_two_seed_entries(self):
        self.assertGreaterEqual(len(V.discover_entries(REPO_ROOT)), 2)


class MalformedInputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "docs").mkdir()
        for stem in ["05-experiment-design", "07-statistical-analysis", "08-evaluation"]:
            (self.tmp / "docs" / f"{stem}.md").write_text("x", encoding="utf-8")
        self.stems = V.docs_stems(self.tmp)

    def test_valid_entry_passes(self):
        self.assertEqual(V.validate_entry(_write(self.tmp), self.stems), [])

    def test_digest_is_crlf_invariant(self):
        self.assertEqual(V.content_digest("a\nb\n"), V.content_digest("a\r\nb\r\n"))

    def test_filename_must_equal_version(self):
        p = _write(self.tmp, ver="1.0.0", fname="9.9.9.md")
        self.assertTrue(any("filename" in e for e in V.validate_entry(p, self.stems)))

    def test_established_requires_citations(self):
        p = _write(self.tmp, status="established", cites="[]")
        self.assertTrue(any("citation" in e.lower() for e in V.validate_entry(p, self.stems)))

    def test_lifecycle_stages_optional(self):
        self.assertEqual(V.validate_entry(_write(self.tmp, stages="[]"), self.stems), [])

    def test_lifecycle_stage_must_match_docs_stem(self):
        p = _write(self.tmp, stages="[05-experimant-design]")
        self.assertTrue(any("lifecycle" in e.lower() for e in V.validate_entry(p, self.stems)))

    def test_bad_evidence_status_rejected(self):
        p = _write(self.tmp, status="totally-made-up")
        self.assertTrue(any("evidence_status" in e for e in V.validate_entry(p, self.stems)))

    def test_missing_body_section_rejected(self):
        p = _write(self.tmp)
        p.write_text(p.read_text(encoding="utf-8").replace("## Limitations\nx\n", ""),
                     encoding="utf-8")
        self.assertTrue(any("Limitations" in e for e in V.validate_entry(p, self.stems)))

    def test_id_must_match_directory(self):
        p = _write(self.tmp, id_="sample-play")
        moved = p.parent.parent / "other-id" / "1.0.0.md"
        moved.parent.mkdir(parents=True, exist_ok=True)
        moved.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertTrue(any("parent directory" in e for e in V.validate_entry(moved, self.stems)))

    def test_main_reports_malformed_entry_without_crashing(self):
        # A malformed entry must produce a non-zero exit via the reported
        # `path: reason` errors, not an uncaught traceback from build_index.
        bad = self.tmp / "playbooks" / "entries" / "broken-play" / "1.0.0.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("no frontmatter here\n", encoding="utf-8")
        self.assertEqual(V.main([], repo_root=self.tmp), 1)
        self.assertEqual(V.main(["--emit-index"], repo_root=self.tmp), 1)
        # ...and it must not have written an index built from invalid content.
        self.assertFalse((self.tmp / "playbooks" / "registry.json").exists())


class ImmutabilityTest(unittest.TestCase):
    """Pins check_index against a real tampered tree, so a regression that
    stopped detecting drift (e.g. check_index returning []) fails the suite."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _emit(self):
        idx = self.tmp / "playbooks" / "registry.json"
        idx.write_text(V._dumps(V.build_index(self.tmp)), encoding="utf-8")

    def test_published_pair_mutation_rejected(self):
        p = _write(self.tmp)
        self._emit()
        self.assertEqual(V.check_index(self.tmp), [])          # clean baseline
        p.write_text(p.read_text(encoding="utf-8").replace("# Sample", "# Sample MUTATED"),
                     encoding="utf-8")
        self.assertTrue(V.check_index(self.tmp))               # digest drift caught

    def test_published_pair_removal_rejected(self):
        _write(self.tmp, id_="alpha-play")
        p2 = _write(self.tmp, id_="beta-play")
        self._emit()
        self.assertEqual(V.check_index(self.tmp), [])          # clean baseline
        p2.unlink()                                            # file gone, row kept
        self.assertTrue(V.check_index(self.tmp))               # missing pair caught


class DeprecationTest(unittest.TestCase):
    """Deprecation lives in the hand-maintained ledger (deprecations.json) and is
    projected into the generated index, because the entry file is immutable."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _write_ledger(self, deprecations):
        p = self.tmp / "playbooks" / "deprecations.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"schemaVersion": 1, "deprecations": deprecations}),
                     encoding="utf-8")

    def test_absent_ledger_means_deprecated_null(self):
        _write(self.tmp, id_="alpha-play")
        row = V.build_index(self.tmp)["entries"][0]
        self.assertIsNone(row["deprecated"])

    def test_ledger_record_projected_into_index(self):
        _write(self.tmp, id_="alpha-play")
        self._write_ledger([{
            "id": "alpha-play", "version": "1.0.0", "since": "2026-09-08",
            "reason": "Superseded.", "superseded_by": "1.1.0",
        }])
        row = V.build_index(self.tmp)["entries"][0]
        self.assertEqual(row["deprecated"], {
            "since": "2026-09-08", "reason": "Superseded.", "superseded_by": "1.1.0",
        })

    def test_superseded_by_optional(self):
        _write(self.tmp, id_="alpha-play")
        self._write_ledger([{
            "id": "alpha-play", "version": "1.0.0", "since": "2026-09-08",
            "reason": "Found wrong.",
        }])
        self.assertEqual([], V.validate_deprecations(self.tmp, {("alpha-play", "1.0.0")}))
        self.assertIsNone(V.build_index(self.tmp)["entries"][0]["deprecated"]["superseded_by"])

    def test_missing_required_field_rejected(self):
        _write(self.tmp, id_="alpha-play")
        self._write_ledger([{"id": "alpha-play", "version": "1.0.0", "since": "2026-09-08"}])
        errs = V.validate_deprecations(self.tmp, {("alpha-play", "1.0.0")})
        self.assertTrue(any("reason" in e for e in errs))

    def test_unknown_entry_reference_rejected(self):
        _write(self.tmp, id_="alpha-play")
        self._write_ledger([{
            "id": "ghost-play", "version": "1.0.0", "since": "2026-09-08", "reason": "x",
        }])
        errs = V.validate_deprecations(self.tmp, {("alpha-play", "1.0.0")})
        self.assertTrue(any("unknown entry" in e for e in errs))

    def test_duplicate_deprecation_rejected(self):
        rec = {"id": "alpha-play", "version": "1.0.0", "since": "2026-09-08", "reason": "x"}
        self._write_ledger([rec, dict(rec)])
        errs = V.validate_deprecations(self.tmp, {("alpha-play", "1.0.0")})
        self.assertTrue(any("duplicate" in e for e in errs))

    def test_handset_deprecated_field_without_ledger_caught(self):
        # A hand-edit that sets registry.json's deprecated field with no backing
        # ledger record must not survive check_index (rebuild has it null).
        _write(self.tmp, id_="alpha-play")
        idx = self.tmp / "playbooks" / "registry.json"
        idx.write_text(V._dumps(V.build_index(self.tmp)), encoding="utf-8")
        self.assertEqual(V.check_index(self.tmp), [])
        tampered = json.loads(idx.read_text(encoding="utf-8"))
        tampered["entries"][0]["deprecated"] = {"since": "x", "reason": "y", "superseded_by": None}
        idx.write_text(V._dumps(tampered), encoding="utf-8")
        self.assertTrue(V.check_index(self.tmp))


if __name__ == "__main__":
    unittest.main()
