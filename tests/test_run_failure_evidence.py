"""A crashed run is still a recorded run.

The Autoresearch Sandbox Gate says failures are results: when an experiment
raises, the runner must still append exactly one ledger row, write a log that
names the error, and dispose of the sandbox. This test drives that failure path
end to end with a deliberately crashing experiment.
"""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import experiments.run_experiment as runner
from experiments.config import ExperimentConfig


class CrashedRunEvidenceTest(unittest.TestCase):
    def test_crashed_run_leaves_ledger_row_log_and_no_sandbox(self) -> None:
        seen = {}

        def crashing_experiment(config, sandbox):
            seen["sandbox_path"] = sandbox.path
            sandbox.write_text("partial.txt", "written before the crash\n")
            raise RuntimeError("boom")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with mock.patch.object(runner, "get_experiment", return_value=crashing_experiment):
                row = runner.run(ExperimentConfig(seed=3, num_records=4), results_dir=tmp_path)

            # The run is reported as an error, not dropped or retried silently.
            self.assertEqual(row["status"], "error")
            self.assertEqual(row["synthetic"], "true")
            self.assertEqual(row["num_records"], 1)

            # Exactly one ledger row, and it is this run's error row.
            with (tmp_path / "ledger.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["run_id"], row["run_id"])
            self.assertEqual(rows[0]["status"], "error")

            # The log exists and records the failure instead of invented data.
            log_path = tmp_path / "logs" / f"{row['run_id']}.jsonl"
            self.assertTrue(log_path.is_file())
            records = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["status"], "error")
            self.assertIn("boom", records[0]["error"])
            self.assertNotIn("synthetic_value", records[0])

        # The sandbox is disposed of even though the experiment crashed.
        self.assertIn("sandbox_path", seen)
        self.assertFalse(seen["sandbox_path"].exists())


if __name__ == "__main__":
    unittest.main()
