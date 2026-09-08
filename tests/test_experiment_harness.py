"""Tests for the sandboxed autoresearch experiment harness.

These verify the safety and reproducibility properties the harness promises:
the sandbox contains writes, live mode is fail-closed, synthetic runs are
deterministic, and every run appends exactly one ledger row plus a log.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiments.config import ConfigError, ExperimentConfig, load_config
from experiments.experiment import example_synthetic, get_experiment, registered_names
from experiments.ledger import LEDGER_FIELDS, append_ledger_row, ensure_ledger, write_log
from experiments.workspace import Sandbox, SandboxViolation


class ConfigTest(unittest.TestCase):
    def test_default_is_synthetic(self) -> None:
        cfg = load_config(env={})
        self.assertEqual(cfg.mode, "synthetic")
        self.assertTrue(cfg.synthetic)

    def test_invalid_mode_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(env={"EXPERIMENT_RUN_MODE": "bogus"})

    def test_live_requires_auth(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(env={"EXPERIMENT_RUN_MODE": "live"})

    def test_live_requires_existing_auth_file(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(
                env={
                    "EXPERIMENT_RUN_MODE": "live",
                    "EXPERIMENT_AUTH": "docs/does-not-exist.md",
                    "EXPERIMENT_CREDENTIAL": "SOME_TOKEN",
                    "SOME_TOKEN": "x",
                }
            )

    def test_live_requires_present_credential(self) -> None:
        # Use a real existing repo file as the authorization reference.
        with self.assertRaises(ConfigError):
            load_config(
                env={
                    "EXPERIMENT_RUN_MODE": "live",
                    "EXPERIMENT_AUTH": "docs/00-beryl-provenance.md",
                    "EXPERIMENT_CREDENTIAL": "MISSING_TOKEN",
                }
            )

    def test_live_never_falls_back_to_synthetic(self) -> None:
        # A misconfigured live run raises, it does not silently downgrade.
        try:
            load_config(env={"EXPERIMENT_RUN_MODE": "live"})
        except ConfigError:
            return
        self.fail("live misconfiguration must raise, not fall back to synthetic")


class SandboxTest(unittest.TestCase):
    def test_write_stays_inside(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Sandbox("run-1", root=Path(tmp)).create()
            target = box.write_text("sub/dir/file.txt", "hello")
            self.assertTrue(target.exists())
            self.assertTrue(str(target).startswith(str(box.path)))
            box.cleanup()
            self.assertFalse(box.path.exists())

    def test_escape_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Sandbox("run-2", root=Path(tmp)).create()
            with self.assertRaises(SandboxViolation):
                box.resolve("../escape.txt")
            with self.assertRaises(SandboxViolation):
                box.resolve("../../etc/passwd")

    def test_context_manager_disposes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with Sandbox("run-3", root=Path(tmp)) as box:
                path = box.path
                self.assertTrue(path.exists())
            self.assertFalse(path.exists())


class SyntheticExperimentTest(unittest.TestCase):
    def test_registered(self) -> None:
        self.assertIn("example-synthetic", registered_names())
        self.assertIs(get_experiment("example-synthetic"), example_synthetic)

    def test_deterministic(self) -> None:
        cfg = ExperimentConfig(seed=42, num_records=6)
        with tempfile.TemporaryDirectory() as tmp:
            a = example_synthetic(cfg, Sandbox("a", root=Path(tmp)).create())
            b = example_synthetic(cfg, Sandbox("b", root=Path(tmp)).create())
        self.assertEqual(a, b, "same seed must produce identical synthetic records")

    def test_all_records_marked_synthetic(self) -> None:
        cfg = ExperimentConfig(seed=1, num_records=5)
        with tempfile.TemporaryDirectory() as tmp:
            records = example_synthetic(cfg, Sandbox("c", root=Path(tmp)).create())
        self.assertEqual(len(records), 5)
        self.assertTrue(all(r["synthetic"] is True for r in records))


class LedgerTest(unittest.TestCase):
    def test_ledger_header_and_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.csv"
            ensure_ledger(ledger)
            header = ledger.read_text(encoding="utf-8").splitlines()[0]
            self.assertEqual(header, ",".join(LEDGER_FIELDS))

            row = {f: "" for f in LEDGER_FIELDS}
            row.update(
                {
                    "run_id": "r1",
                    "timestamp_utc": "2026-01-01T00:00:00Z",
                    "mode": "synthetic",
                    "experiment": "example-synthetic",
                    "config_hash": "abc123",
                    "synthetic": "true",
                    "num_records": 3,
                    "status": "ok",
                    "notes": "",
                }
            )
            append_ledger_row(row, ledger)
            lines = [ln for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2, "exactly one data row appended")

    def test_append_rejects_incomplete_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.csv"
            with self.assertRaises(ValueError):
                append_ledger_row({"run_id": "r1"}, ledger)

    def test_write_log_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            logs = Path(tmp) / "logs"
            path = write_log("r1", [{"a": 1}, {"a": 2}], logs)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)


class RunnerEndToEndTest(unittest.TestCase):
    def test_full_synthetic_run_writes_ledger_and_log(self) -> None:
        import experiments.run_experiment as runner

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            row = runner.run(ExperimentConfig(seed=7, num_records=4), results_dir=tmp_path)
            self.assertEqual(row["status"], "ok")
            self.assertEqual(row["num_records"], 4)
            self.assertEqual(row["synthetic"], "true")
            lines = [
                ln
                for ln in (tmp_path / "ledger.csv").read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            self.assertEqual(len(lines), 2)
            self.assertTrue((tmp_path / "logs" / f"{row['run_id']}.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
