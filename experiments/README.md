# Experiment Harness

This is the sandboxed autoresearch pipeline. It runs an experiment automatically inside a disposable workspace the repository creates, writes a deterministic per-run log, and appends one audit row to `results/ledger.csv`. It is the only automatic writer of experiment output, and it never fabricates data.

## Run it

```bash
python3 -m experiments.run_experiment
```

That runs the default `example-synthetic` experiment: a deterministic, offline synthetic run that needs no credentials and no network. It writes `results/logs/<run_id>.jsonl` and appends one row to `results/ledger.csv` with `synthetic=true`.

List the registered experiments:

```bash
python3 -m experiments.run_experiment --list
```

## Configuration

Everything is configured from the environment, so a run is reproducible from its recorded configuration alone.

| Variable | Default | Meaning |
| --- | --- | --- |
| `EXPERIMENT_RUN_MODE` | `synthetic` | `synthetic` (offline, deterministic) or `live`. |
| `EXPERIMENT_NAME` | `example-synthetic` | The registered experiment to run. |
| `EXPERIMENT_SEED` | `0` | Seed for deterministic synthetic runs. |
| `EXPERIMENT_NUM_RECORDS` | `8` | Number of records the synthetic experiment emits. |
| `EXPERIMENT_AUTH` | (unset) | Repo-relative path to a dated authorization doc. Required for `live`. |
| `EXPERIMENT_CREDENTIAL` | (unset) | Name of the env var holding the live credential. Required for `live`. |
| `EXPERIMENT_NOTES` | (unset) | Free-text note recorded in the ledger row. |

## Sandbox and safety rules

- Each run executes only inside `experiments/workspaces/<run_id>/`. The `Sandbox` refuses any path that resolves outside that directory (`SandboxViolation`). The runner writes only under `experiments/` and `results/`.
- Synthetic mode is the default. A `live` run is **fail-closed**: it requires `EXPERIMENT_AUTH` to point at a file that exists in the repository and `EXPERIMENT_CREDENTIAL` to name a present, non-empty environment variable. If either is missing the run is refused. There is no silent fallback to synthetic.
- Every run appends exactly one row to `results/ledger.csv` and writes a log under `results/logs/`. A result not traceable to a ledger row does not exist.
- The runner never writes into the results templates (`results/participants.csv`, `results/measurements.csv`) or `docs/06-experimental-results.md`. Promoting a run's output into the study's results is a deliberate, human-reviewed step.
- Timeouts, refusals, and errors are recorded as results, not hidden.

## Making it your experiment

Replace `example-synthetic` in `experiment.py` with the protocol from `docs/05-experiment-design.md`:

1. Write a function `def my_experiment(config, sandbox) -> list[dict]` and decorate it with `@register("my-name")`.
2. Return one record dict per unit; include `status` and any measured fields. Do not invent values.
3. For a live experiment, read the fail-closed configuration and use `config.credential_name` to reach your real credential; keep all work inside the sandbox.
4. Add or update tests in `../tests/` and run the verification gate.

## Layout

```
experiments/
  run_experiment.py   entry point / orchestrator
  config.py           env-driven configuration, fail-closed live validation
  workspace.py        disposable sandbox with escape protection
  experiment.py       registry + the synthetic example experiment
  ledger.py           append-one-row ledger + per-run JSONL log writer
  workspaces/         disposable per-run sandboxes (gitignored)
```
