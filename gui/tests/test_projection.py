"""The overview read model: matches the contract, isolates failures, never writes."""
import datetime as dt
import unittest

from gui.server import projection
from gui.tests import schema_check
from gui.tests.fixtures import LEDGER_HEADER, make_repo, snapshot
from gui.tests.test_sources import ROW_ERR, ROW_OK

NOW = dt.datetime(2026, 9, 28, 6, 0, tzinfo=dt.timezone.utc)
SCHEMA = schema_check.load("overview.schema.json")


class OverviewTest(unittest.TestCase):
    def assertValid(self, ov):
        self.assertEqual(schema_check.errors(ov, SCHEMA), [])

    def test_template_repo(self):
        tmp, root = make_repo()
        with tmp:
            ov = projection.build_overview(root, NOW)
            self.assertValid(ov)
            self.assertIsNone(ov["project"]["researchQuestion"])
            self.assertEqual(ov["project"]["stage"], {"tracked": False})
            self.assertEqual(ov["findings"], {"tracked": False})
            self.assertEqual(ov["decisions"], {"tracked": False})
            self.assertEqual(ov["work"], [])

    def test_runs_become_work_items(self):
        tmp, root = make_repo(**{"results/ledger.csv": LEDGER_HEADER + ROW_OK + ROW_ERR})
        with tmp:
            ov = projection.build_overview(root, NOW)
            self.assertValid(ov)
            statuses = [w["status"] for w in ov["work"]]
            self.assertEqual(sorted(statuses), ["failed", "ok"])
            failed = next(w for w in ov["work"] if w["status"] == "failed")
            self.assertEqual(failed["actions"], [])  # nothing can be carried out yet
            self.assertFalse(failed["synthetic"])
            runs = next(s for s in ov["pipeline"] if s["stage"] == "Runs")
            self.assertEqual(runs["counts"][0], ["ok", 1])
            self.assertEqual(runs["counts"][1][:2], ["failed", 1])

    def test_unknown_statuses_are_not_guessed(self):
        odd = "20260928T030000-live-cccc3333,2026-09-28T03:00:00Z,live,x,y,false,1,timeout,\n"
        tmp, root = make_repo(**{"results/ledger.csv": LEDGER_HEADER + odd})
        with tmp:
            ov = projection.build_overview(root, NOW)
            self.assertEqual(ov["work"], [])
            self.assertTrue(any("timeout" in w for w in ov["warnings"]))

    def test_broken_sources_stay_contained(self):
        tmp, root = make_repo(**{"results/ledger.csv": "garbage\n", "references.md": None, "readingList.md": None,
                                 "docs/03-research-question.md": "## The one main research question\n\n> Real question?\n"})
        with tmp:
            ov = projection.build_overview(root, NOW)
            self.assertValid(ov)
            self.assertEqual(ov["project"]["researchQuestion"], "Real question?")  # unaffected
            self.assertFalse(ov["actions"]["available"])
            runs = next(s for s in ov["pipeline"] if s["stage"] == "Runs")
            self.assertFalse(runs["available"])
            evidence = next(s for s in ov["pipeline"] if s["stage"] == "Evidence")
            self.assertFalse(evidence["available"])

    def test_never_writes(self):
        tmp, root = make_repo(**{"results/ledger.csv": LEDGER_HEADER + ROW_OK + ROW_ERR})
        with tmp:
            before = snapshot(root)
            projection.build_overview(root, NOW)
            self.assertEqual(snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
