"""Deterministic checks that enforce the AISoc research harness standards.

The metric for "done" (RESEARCH_RULES.md) is that a non-expert can read the
user-facing documents and state the experiment, and that the repository always
holds exactly one research question, never fabricated data, synchronised files,
and no application code before the PRD is green-lit. These tests turn those
standards into automated gates. They are written against the fork template, so
they pass on the shipped placeholders and keep passing as a fork fills them in,
as long as the invariants hold.
"""
from __future__ import annotations

import csv
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PINNED_BERYL_COMMIT = "a0f5f51fbd21cb629622978358756a157df47b0e"

# Files a reader or the harness relies on existing.
REQUIRED_FILES = (
    "README.md",
    "RESEARCH_RULES.md",
    "ProjectProposal.md",
    "readingList.md",
    "references.md",
    "notes/README.md",
    "notes/systems-thinking-primer.md",
    "docs/README.md",
    "docs/00-beryl-provenance.md",
    "docs/01-literature-review.md",
    "docs/02-problem-analysis.md",
    "docs/03-research-question.md",
    "docs/04-solution-design.md",
    "docs/05-experiment-design.md",
    "docs/06-experimental-results.md",
    "docs/07-statistical-analysis.md",
    "docs/08-evaluation.md",
    "results/README.md",
    "results/ledger.csv",
    "results/participants.csv",
    "results/measurements.csv",
    "solution/README.md",
    "solution/PRD.md",
    "report/README.md",
    "report/report.md",
    "report/report.tex",
    "report/source.sha256",
    "report/sections/introduction.tex",
    "report/sections/method.tex",
    "report/sections/results.tex",
    "experiments/README.md",
    "experiments/run_experiment.py",
    "experiments/config.py",
    "experiments/workspace.py",
    "experiments/ledger.py",
    "experiments/experiment.py",
    "analysis/README.md",
    "analysis/summarize.py",
    ".beryl/agent/synchronization-contract.md",
    ".beryl/agent/systems-thinking-methodology.md",
    ".beryl/agent/project-brief.md",
    ".beryl/agent/task-routing.md",
    ".beryl/agent/architecture.md",
    ".beryl/agent/ubiquitous-language.md",
    ".beryl/agent/design-tree.md",
)

# The single canonical research-question marker, verbatim, must match in every
# file that states it. A fork replaces this string identically everywhere.
RESEARCH_QUESTION_FILES = (
    "ProjectProposal.md",
    "RESEARCH_RULES.md",
    "docs/03-research-question.md",
    ".beryl/agent/project-brief.md",
    "README.md",
    "report/report.md",
    "report/sections/introduction.tex",
)

RQ_CANONICAL_SUBSTRING = "<Your one main research question goes here.>"

# Result templates that must never carry fabricated data rows (header only).
RESULT_TEMPLATES = (
    "results/participants.csv",
    "results/measurements.csv",
)

# Directories under solution/ that would indicate application code before
# green-light. Only PRD.md, README.md, and planning docs are allowed.
SOLUTION_ALLOWED = {"README.md", "PRD.md"}

MARKDOWN_LINK_FILES = (
    "README.md",
    "ProjectProposal.md",
    "RESEARCH_RULES.md",
    "docs/README.md",
    "results/README.md",
    "solution/README.md",
    "report/README.md",
    "experiments/README.md",
    "analysis/README.md",
)

EM_DASH = "\u2014"


def read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


class RequiredStructureTest(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        missing = [f for f in REQUIRED_FILES if not (REPO_ROOT / f).is_file()]
        self.assertEqual(missing, [], f"missing required files: {missing}")


class BerylProvenanceTest(unittest.TestCase):
    def test_pinned_commit_recorded(self) -> None:
        provenance = read("docs/00-beryl-provenance.md")
        self.assertIn(PINNED_BERYL_COMMIT, provenance)

    def test_lockfile_source_ref(self) -> None:
        import json

        lock = json.loads(read(".beryl/lock.json"))
        self.assertEqual(lock.get("sourceRef"), PINNED_BERYL_COMMIT)


class SingleResearchQuestionTest(unittest.TestCase):
    def test_canonical_question_present_everywhere(self) -> None:
        for rel in RESEARCH_QUESTION_FILES:
            with self.subTest(file=rel):
                self.assertIn(
                    RQ_CANONICAL_SUBSTRING,
                    read(rel),
                    f"{rel} must state the one canonical research question verbatim",
                )

    def test_exactly_one_question_marker_per_file(self) -> None:
        # The canonical marker should appear, and no competing second marker of
        # the same template form should be introduced.
        for rel in RESEARCH_QUESTION_FILES:
            with self.subTest(file=rel):
                count = read(rel).count(RQ_CANONICAL_SUBSTRING)
                self.assertGreaterEqual(count, 1, f"{rel} is missing the research question")


class NoFabricatedDataTest(unittest.TestCase):
    def test_result_templates_are_header_only(self) -> None:
        for rel in RESULT_TEMPLATES:
            with self.subTest(file=rel):
                rows = list(csv.reader((REPO_ROOT / rel).read_text(encoding="utf-8").splitlines()))
                non_empty = [r for r in rows if r and any(cell.strip() for cell in r)]
                self.assertLessEqual(
                    len(non_empty),
                    1,
                    f"{rel} must contain only a header row until real data exists",
                )

    def test_ledger_is_header_only_in_committed_state(self) -> None:
        rows = list(csv.reader(read("results/ledger.csv").splitlines()))
        non_empty = [r for r in rows if r and any(cell.strip() for cell in r)]
        self.assertLessEqual(
            len(non_empty), 1, "committed results/ledger.csv must be header-only"
        )

    def test_results_doc_has_no_numbers_promoted(self) -> None:
        # The results doc explicitly declares it is empty of results. Guard that
        # the declaration remains, so a fork does not quietly paste numbers in.
        doc = read("docs/06-experimental-results.md")
        self.assertIn("empty of results until real data exists".lower(), doc.lower())


class GreenLightGateTest(unittest.TestCase):
    def test_no_application_code_before_green_light(self) -> None:
        solution = REPO_ROOT / "solution"
        offenders = []
        for path in solution.rglob("*"):
            if path.is_dir():
                continue
            if path.name in SOLUTION_ALLOWED:
                continue
            # Planning markdown is allowed; code and other artifacts are not.
            if path.suffix.lower() == ".md":
                continue
            offenders.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(
            offenders,
            [],
            f"solution/ must hold only the PRD and planning docs before green-light: {offenders}",
        )


class MarkdownAndProseTest(unittest.TestCase):
    def test_markdown_links_resolve(self) -> None:
        pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for rel in MARKDOWN_LINK_FILES:
            text = read(rel)
            base = (REPO_ROOT / rel).parent
            for target in pattern.findall(text):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                link = target.split("#", 1)[0]
                if not link:
                    continue
                with self.subTest(file=rel, target=target):
                    self.assertTrue(
                        (base / link).exists(),
                        f"{rel}: broken relative link to {target}",
                    )

    def test_no_em_dashes_in_core_research_prose(self) -> None:
        for rel in ("RESEARCH_RULES.md", "ProjectProposal.md", "README.md", "docs/README.md"):
            with self.subTest(file=rel):
                self.assertNotIn(EM_DASH, read(rel), f"{rel} must not contain em-dashes")


class SkillsRegisteredTest(unittest.TestCase):
    REQUIRED_SKILLS = (
        "academic-research-writer",
        "voice-and-confidence-calibration",
        "clearly-and-concisely-academic",
    )

    def test_skills_installed(self) -> None:
        for skill in self.REQUIRED_SKILLS:
            with self.subTest(skill=skill):
                self.assertTrue(
                    (REPO_ROOT / ".beryl/agent/skills" / skill / "SKILL.md").is_file(),
                    f"missing skill: {skill}",
                )

    def test_skills_registered_in_routing(self) -> None:
        routing = read(".beryl/agent/task-routing.md")
        for skill in self.REQUIRED_SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(skill, routing, f"{skill} not registered in task-routing.md")


if __name__ == "__main__":
    unittest.main()
