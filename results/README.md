# Results

Structured result logs, the run ledger, and empty data templates. **Everything here is a template or an audit record. No data is fabricated** (RESEARCH_RULES.md). Data rows in the CSV templates are added only when real, user-provided data exists or is produced by the sandboxed runner in `experiments/` and traced through `ledger.csv`.

## What is here

| Path | One row per | Purpose |
| --- | --- | --- |
| [ledger.csv](ledger.csv) | experiment run | The audit trail. Every run of `experiments/run_experiment.py` appends exactly one row. A result not traceable to a ledger row does not exist. Written by the runner. |
| [evidence/](evidence/) | reviewed run | Immutable hash-addressed JSON archive of an existing runner ledger row and exact log, retained with a reviewed terminal workflow record. Empty until evidence is explicitly promoted. |
| [logs/](logs/) | run | Per-run JSON Lines result logs written by the runner. One `.jsonl` file per run, named by `run_id`. |
| [participants.csv](participants.csv) | participant / subject | Anonymous code and condition. No identifying data. Header-only template. |
| [measurements.csv](measurements.csv) | observation | The outcome metric and any covariates, keyed by subject and condition. Header-only template. |

## Rules

- A template `*.csv` (everything except `ledger.csv`) must contain only a header row until real data exists. The harness test suite fails if a template CSV has data rows (see `tests/test_harness_standards.py::NoFabricatedDataTest`).
- `ledger.csv` is an audit record written by the runner. In synthetic mode its rows are marked `synthetic=true`. It is never hand-edited to add results.
- No participant-identifying data is stored here; subjects are keyed by anonymous code only.
- Figures and summary tables are generated from these files by the scripts in `analysis/` once data exists, then recorded in `docs/06-experimental-results.md` and mirrored into `report/figures/`.

## Ledger schema

`ledger.csv` columns: `run_id`, `timestamp_utc`, `mode`, `experiment`, `config_hash`, `synthetic`, `num_records`, `status`, `notes`.

## Reviewed run evidence

Runtime logs are ignored by Git and the committed ledger may remain header-only. A terminal workflow record therefore requires a reviewed archive under `evidence/RUN_ID/SHA256.json`. Use `python3 -m workflow run-reference --run-id EXISTING_RUN_ID --archive` to derive the archive and record details from existing runner output without writing files, then include the returned archive text in the terminal record proposal. See the [workflow command guide](../workflow/README.md). The archive retains one exact ledger row, the original source paths, and exact log bytes; it does not hand-edit the runner ledger or logs. Its synthetic marker remains intact. Approved archives are immutable and remain available to CI and retained record revisions after runtime files are absent. Do not retain secrets or participant-identifying data. Promoting actual study results into research conclusions still follows the synchronization contract.
