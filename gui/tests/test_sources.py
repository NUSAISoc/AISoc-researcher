"""Each source reader on its own: correct values, and failures that stay contained."""
import unittest

from gui.server.sources import ledger, reading_list, references, research_question, results_templates
from gui.tests.fixtures import LEDGER_HEADER, make_repo

ROW_OK = "20260928T010000-synthetic-aaaa1111,2026-09-28T01:00:00Z,synthetic,example-synthetic,abc,true,8,ok,\n"
ROW_ERR = "20260928T020000-live-bbbb2222,2026-09-28T02:00:00Z,live,example-synthetic,def,false,1,error,boom\n"


class ResearchQuestionTest(unittest.TestCase):
    def test_template_means_not_set(self):
        tmp, root = make_repo()
        with tmp:
            r = research_question.read(root)
            self.assertTrue(r.ok)
            self.assertIsNone(r.value)

    def test_real_question_with_crlf(self):
        tmp, root = make_repo(**{"docs/03-research-question.md": "## The one main research question\r\n\r\n> Does X improve Y?\r\n"})
        with tmp:
            self.assertEqual(research_question.read(root).value, "Does X improve Y?")

    def test_missing_heading_is_a_contained_failure(self):
        tmp, root = make_repo(**{"docs/03-research-question.md": "# Nothing here\n"})
        with tmp:
            r = research_question.read(root)
            self.assertFalse(r.ok)
            self.assertIn("heading", r.reason)

    def test_missing_file(self):
        tmp, root = make_repo(**{"docs/03-research-question.md": None})
        with tmp:
            self.assertFalse(research_question.read(root).ok)


class EvidenceTest(unittest.TestCase):
    def test_templates_are_ignored(self):
        tmp, root = make_repo()
        with tmp:
            self.assertEqual(references.read(root).value["total"], 0)
            self.assertEqual(reading_list.read(root).value, 0)

    def test_counts_by_depth(self):
        refs = "## All Readings Read So Far\n\n1. Smith (2020). A. [full]\n2. Lee (2021). B. [abstract]\n3. Kim (2022). C.\n\n## Other\n\n1. Not counted [full]\n"
        lst = "| A | B | C |\n| --- | --- | --- |\n| Wu (2023), T | why | 1 |\n| Ng (2024), U | why | 2 |\n"
        tmp, root = make_repo(**{"references.md": refs, "readingList.md": lst})
        with tmp:
            v = references.read(root).value
            self.assertEqual(v["total"], 3)
            self.assertEqual(v["byDepth"]["full"], 1)
            self.assertEqual(v["byDepth"]["untagged"], 1)
            self.assertEqual(reading_list.read(root).value, 2)


class LedgerTest(unittest.TestCase):
    def test_rows_and_status(self):
        tmp, root = make_repo(**{"results/ledger.csv": LEDGER_HEADER + ROW_OK + ROW_ERR})
        with tmp:
            r = ledger.read(root)
            self.assertTrue(r.ok)
            self.assertEqual([x["status"] for x in r.value], ["ok", "error"])

    def test_missing_columns_is_contained(self):
        tmp, root = make_repo(**{"results/ledger.csv": "a,b\n1,2\n"})
        with tmp:
            r = ledger.read(root)
            self.assertFalse(r.ok)
            self.assertIn("missing columns", r.reason)

    def test_unusual_run_id_skipped_with_warning(self):
        bad = "../../etc/passwd,2026-09-28T01:00:00Z,live,x,y,false,1,ok,\n"
        tmp, root = make_repo(**{"results/ledger.csv": LEDGER_HEADER + bad + ROW_OK})
        with tmp:
            r = ledger.read(root)
            self.assertEqual(len(r.value), 1)
            self.assertEqual(len(r.warnings), 1)

    def test_log_path_only_for_ledger_ids(self):
        tmp, root = make_repo(**{"results/ledger.csv": LEDGER_HEADER + ROW_OK})
        with tmp:
            rid = "20260928T010000-synthetic-aaaa1111"
            (root / "results/logs" / f"{rid}.jsonl").write_text("{}\n")
            (root / "results/logs" / "other.jsonl").write_text("{}\n")
            rows = ledger.read(root).value
            self.assertIsNotNone(ledger.log_path(root, rid, rows))
            self.assertIsNone(ledger.log_path(root, "other", rows))
            self.assertIsNone(ledger.log_path(root, "../ledger", rows))


class ResultTemplatesTest(unittest.TestCase):
    def test_header_only_means_no_data(self):
        tmp, root = make_repo()
        with tmp:
            self.assertEqual(results_templates.read(root).value, {"hasData": False})

    def test_rows_mean_data(self):
        tmp, root = make_repo(**{"results/participants.csv": "a,b\nP01,treatment\n"})
        with tmp:
            self.assertEqual(results_templates.read(root).value, {"hasData": True})


if __name__ == "__main__":
    unittest.main()
