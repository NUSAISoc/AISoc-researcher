"""Entry point for the sandboxed autoresearch runner.

Run the full pipeline with:

    python3 -m experiments.run_experiment

It loads the configuration from the environment, creates a disposable sandbox,
runs the selected experiment inside it, writes a per-run JSON Lines log, appends
one row to ``results/ledger.csv``, and disposes of the sandbox. Synthetic mode
is the default and needs no credentials or network. A live run is fail-closed:
if authorization or credentials are missing it aborts, and never silently falls
back to synthetic.

The runner writes only under ``experiments/`` and ``results/``. It never writes
into the results templates or ``docs/06``; promoting a run's output into the
study's results is a deliberate, human-reviewed step.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
import uuid
from pathlib import Path
from typing import List, Mapping

from .config import ConfigError, ExperimentConfig, load_config
from .experiment import get_experiment, registered_names
from .ledger import append_ledger_row, write_log
from .workspace import Sandbox


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_run_id(config: ExperimentConfig) -> str:
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{config.mode}-{uuid.uuid4().hex[:8]}"


def run(config: ExperimentConfig, results_dir: "Path | None" = None) -> dict:
    """Execute one experiment run end to end and return its ledger row.

    ``results_dir`` overrides where the ledger and logs are written. It defaults
    to the repository's ``results/`` directory. Tests pass a temporary directory
    so a run never touches the committed results state.
    """
    from .config import RESULTS_DIR

    out_dir = RESULTS_DIR if results_dir is None else Path(results_dir)
    ledger_path = out_dir / "ledger.csv"
    logs_dir = out_dir / "logs"

    run_id = _new_run_id(config)
    experiment = get_experiment(config.name)

    status = "ok"
    records: List[Mapping[str, object]] = []
    sandbox = Sandbox(run_id).create()
    try:
        records = experiment(config, sandbox)
    except Exception as exc:  # noqa: BLE001 - failures are results, not exclusions
        status = "error"
        records = [{"status": "error", "error": repr(exc), "synthetic": config.synthetic}]
    finally:
        sandbox.cleanup()

    log_path = write_log(run_id, records, logs_dir)

    row = {
        "run_id": run_id,
        "timestamp_utc": _utc_now(),
        "mode": config.mode,
        "experiment": config.name,
        "config_hash": config.config_hash(),
        "synthetic": str(config.synthetic).lower(),
        "num_records": len(records),
        "status": status,
        "notes": config.notes,
    }
    append_ledger_row(row, ledger_path)
    print(f"run {run_id}: status={status} records={len(records)} log={log_path}")
    return row


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sandboxed autoresearch runner")
    parser.add_argument(
        "--list", action="store_true", help="list registered experiments and exit"
    )
    args = parser.parse_args(argv)

    if args.list:
        print("registered experiments:")
        for name in registered_names():
            print(f"  {name}")
        return 0

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    row = run(config)
    return 0 if row["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
