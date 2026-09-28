"""Events from external sources: imported into the central log and displayed."""
import datetime as dt
import unittest

from gui.server import projection
from gui.server.central_log import CentralLog, read_records
from gui.server.sources import event_log
from gui.tests import schema_check
from gui.tests.fixtures import LEDGER_HEADER, event, make_repo, snapshot, write_events

NOW = dt.datetime.now(dt.timezone.utc)
OVERVIEW = schema_check.load("overview.schema.json")
LINE = schema_check.load("event-log.schema.json")
FINDING = {"claim": "Hints help", "effect": "Inferred effect: faster", "uncertainty": "d = 0.4",
           "synthetic": True, "harness": "codex", "model": "model-y"}


class EventViewTest(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = make_repo()
        self.log = CentralLog(self.root / event_log.REL_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def emit(self, *events):
        write_events(self.root, events)
        return self.log.import_file(self.root, "control/events.jsonl")

    def ov(self):
        o = projection.build_overview(self.root, NOW)
        self.assertEqual(schema_check.errors(o, OVERVIEW), [])
        return o

    def test_no_events_means_not_tracked(self):
        o = self.ov()
        self.assertEqual((o["findings"], o["decisions"]), ({"tracked": False}, {"tracked": False}))

    def test_sample_event_matches_the_contract(self):
        self.assertEqual(schema_check.errors(event("finding.inferred", "agent", "s5", "finding", "F1", 1, FINDING), LINE), [])

    def test_finding_lifecycle(self):
        self.emit(event("finding.inferred", "agent", "s5", "finding", "F1", 1, FINDING))
        o = self.ov()
        self.assertEqual((o["findings"][0]["verification"], o["findings"][0]["inferredBy"]["session"]), ("unverified", "s5"))
        stage = next(s for s in o["pipeline"] if s["stage"] == "Findings")
        self.assertEqual(stage["counts"][1], ["to review", 1])
        self.emit(event("finding.verified", "human", "researcher-1", "finding", "F1", 2, {"rationale": "matches rule"}))
        f = self.ov()["findings"][0]
        self.assertEqual((f["verification"], f["reviewedBy"]["name"]), ("verified", "researcher-1"))
        self.emit(event("finding.evidence_changed", "agent", "s5", "finding", "F1", 3, {"reason": "R07 log amended"}))
        f = self.ov()["findings"][0]
        self.assertEqual(f["verification"], "recheck")
        self.assertIn("R07", f["recheckReason"])

    def test_agent_cannot_appear_to_decide(self):
        self.emit(event("finding.inferred", "agent", "s5", "finding", "F1", 1, FINDING),
                  event("finding.verified", "agent", "s5", "finding", "F1", 2, {"rationale": "trust me"}))
        o = self.ov()
        self.assertEqual(o["findings"][0]["verification"], "unverified")
        self.assertTrue(any("only a human can decide" in w for w in o["warnings"]))

    def test_decisions_and_urgency(self):
        self.emit(event("decision.proposed", "agent", "s4", "decision", "D1", 1, {"kind": "protocol", "title": "Approve protocol v3",
                        "blocks": ["R19", "R20"], "pausesAgent": True}))
        d = next(w for w in self.ov()["work"] if w["id"] == "D1")
        self.assertEqual((d["status"], d["type"], d["urgency"]["blocks"], d["urgency"]["paused"]), ("decision", "protocol", 2, True))
        self.emit(event("decision.approved", "human", "researcher-1", "decision", "D1", 2, {"rationale": "fine"}))
        self.assertFalse(any(w["id"] == "D1" for w in self.ov()["work"]))

    def test_runs_from_events(self):
        self.emit(event("run.started", "system", "runner", "run", "R50", 1, {"experiment": "exp", "mode": "live", "unitsTotal": 8}),
                  event("run.progressed", "system", "runner", "run", "R50", 2, {"unitsRecorded": 3}))
        r = next(w for w in self.ov()["work"] if w["id"] == "R50")
        self.assertEqual((r["status"], r["summary"]), ("running", "3 of 8 units recorded"))
        self.emit(event("run.finished", "system", "runner", "run", "R50", 3, {"outcome": "timeout"}))
        self.assertEqual(next(w for w in self.ov()["work"] if w["id"] == "R50")["status"], "failed")

    def test_finished_run_in_ledger_is_not_duplicated(self):
        (self.root / "results/ledger.csv").write_text(LEDGER_HEADER + "R60,2026-09-28T01:00:00Z,live,x,y,false,1,error,\n")
        self.emit(event("run.finished", "system", "runner", "run", "R60", 1, {"outcome": "failure"}))
        self.assertEqual([w["id"] for w in self.ov()["work"]].count("R60"), 1)

    def test_bad_lines_are_kept_but_not_shown(self):
        self.emit(event("finding.inferred", "agent", "s5", "finding", "F1", 1, FINDING))
        write_events(self.root, ["not json", '{"v": 1}'])
        res = self.log.import_file(self.root, "control/events.jsonl")
        self.assertEqual(len(res["rejected"]), 2)
        o = self.ov()
        self.assertEqual(len(o["findings"]), 1)
        self.assertTrue(any("malformed" in w for w in o["warnings"]))
        kinds = [r["kind"] for r in read_records(self.root / event_log.REL_PATH)]
        self.assertEqual(kinds.count("invalid"), 2)

    def test_reading_never_writes(self):
        self.emit(event("finding.inferred", "agent", "s5", "finding", "F1", 1, FINDING))
        before = snapshot(self.root, include_log=True)
        self.ov()
        self.assertEqual(snapshot(self.root, include_log=True), before)


if __name__ == "__main__":
    unittest.main()
