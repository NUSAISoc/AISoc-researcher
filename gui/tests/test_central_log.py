"""The central log: imports external files and API items, keeps everything, never edits."""
import json
import threading
import unittest

from gui.server.central_log import CentralLog, read_records
from gui.server.sources import event_log
from gui.tests.fixtures import event, make_repo, write_events

SRC = "control/events.jsonl"


class CentralLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = make_repo()
        self.log = CentralLog(self.root / event_log.REL_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def records(self):
        return read_records(self.root / event_log.REL_PATH)

    def test_import_is_incremental_and_deduplicated(self):
        e1 = event("run.started", "system", "runner", "run", "R1", 1)
        write_events(self.root, [e1])
        self.assertEqual(self.log.import_file(self.root, SRC)["accepted"], 1)
        self.assertEqual(self.log.import_file(self.root, SRC)["accepted"], 0)  # nothing new
        # the same event arriving through the API is stored once
        self.assertEqual(self.log.add_events("api:x", [e1])["duplicates"], 1)
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(self.records()[0]["source"], "file:" + SRC)

    def test_partial_last_line_waits(self):
        p = self.root / SRC
        p.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event("run.started", "system", "runner", "run", "R2", 1))
        p.write_text(line[:20])
        self.assertEqual(self.log.import_file(self.root, SRC)["accepted"], 0)
        p.write_text(line + "\n")
        self.assertEqual(self.log.import_file(self.root, SRC)["accepted"], 1)

    def test_kept_when_source_is_replaced_or_deleted(self):
        write_events(self.root, [event("run.started", "system", "runner", "run", "R3", 1)])
        self.log.import_file(self.root, SRC)
        (self.root / SRC).write_text(json.dumps(event("run.started", "system", "runner", "run", "R4", 1)) + "\n")
        self.log.import_file(self.root, SRC)  # shorter file: re-read from the start
        (self.root / SRC).unlink()
        self.log.import_file(self.root, SRC)
        ids = sorted(r["entry"]["subject"]["id"] for r in self.records())
        self.assertEqual(ids, ["R3", "R4"])

    def test_source_file_is_never_written(self):
        write_events(self.root, [event("run.started", "system", "runner", "run", "R5", 1)])
        before = (self.root / SRC).read_bytes()
        self.log.import_file(self.root, SRC)
        self.assertEqual((self.root / SRC).read_bytes(), before)

    def test_invalid_items_are_kept_with_reason(self):
        res = self.log.add_events("api:x", [{"v": 2}, "text"])
        self.assertEqual([r["index"] for r in res["rejected"]], [0, 1])
        self.assertEqual([r["kind"] for r in self.records()], ["invalid", "invalid"])

    def test_concurrent_writers_do_not_interleave(self):
        def work(n):
            for i in range(25):
                self.log.add_events(f"api:w{n}", [event("run.progressed", "system", f"w{n}", "run", f"R{n}", i + 1)])
                self.log.add_interaction({"command": f"runs/R{n}:stop", "outcome": {"code": 501}})
        ts = [threading.Thread(target=work, args=(n,)) for n in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        lines = (self.root / event_log.REL_PATH).read_text().splitlines()
        self.assertEqual(len(lines), 200)
        for ln in lines:
            json.loads(ln)  # every line is complete

    def test_gitignore_keeps_the_log_local(self):
        from pathlib import Path
        gi = Path(__file__).resolve().parents[1] / ".gitignore"
        self.assertIn(".local/", gi.read_text().split())


if __name__ == "__main__":
    unittest.main()
