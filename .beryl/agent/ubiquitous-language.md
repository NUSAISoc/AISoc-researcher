# Ubiquitous Language

The shared vocabulary of this research harness. These terms describe the harness itself and are stable across forks. Add your study-specific terms (the intervention, the outcome construct, the instruments) below the harness terms when you fork, and keep them consistent across `docs/`, the proposal, the report, and the PRD.

## Harness terms (stable across forks)

| Term | Definition | Avoid |
| --- | --- | --- |
| Autoresearch harness | This repository: a control plane that holds the research plan, enforces its format, and runs experiments automatically in a sandbox it creates. | "the framework" (be specific) |
| Control plane | Beryl under `.beryl/`: agent memory, task routing, the synchronization contract, and the deterministic check gate. | "the config" |
| Research question | The single main question the study answers. Exactly one at a time, stated identically everywhere it appears. | plural "questions" for the main one |
| Intervention / treatment | The change the study proposes and tests. The treatment condition. | "the solution" before green-light |
| Control condition / baseline | The existing solution or status quo the intervention is compared against. | "the old one" |
| Outcome metric | The dependent measure the study compares between conditions. | "the score" (name it) |
| Green-light | The researcher's explicit approval of the PRD, after which the solution app is built as a submodule under `solution/`. | inferring approval |
| Sandbox | The disposable workspace under `experiments/workspaces/` that the runner creates for each experiment. Nothing outside `experiments/` and `results/` is touched. | "the environment" |
| Ledger | `results/ledger.csv`: one row per experiment run, the audit trail that makes every result traceable. | "the log" (that is the per-run JSONL) |
| Synthetic mode | The default experiment mode: deterministic, offline, no credentials. | "test mode" |
| Live mode | A real experiment run, fail-closed on missing authorization or credentials, never silently falling back to synthetic. | "production mode" |
| User-facing surface | The three documents the researcher reads: `ProjectProposal.md`, `report/`, and `notes/`. | calling `docs/` user-facing |
| Synchronization contract | The completion gate mapping each research boundary to the targets it must be propagated to. | skipping targets |

## Run evidence terms (issue #9)

Accepted in ADRs 0004 to 0009; in use once each implementing PR lands. Campaign and the run lifecycle belong to issue #6.

| Term | Definition | Avoid |
| --- | --- | --- |
| Run status | The final status the runner records in the ledger: `ok`, `error`, `cancelled` (interrupted during execution), `refused` (stopped before the experiment started), `timeout` (stopped at its time limit), or `lost` (its process is known to be gone and it left no final record). | "failed" for every non-`ok` status |
| Open run | A run with a started marker but no final ledger row. Reported as unresolved while its process cannot be confirmed gone. | calling it lost |
| Execution backend | Where a run executes, such as this machine or a Slurm cluster. It runs the experiment and reports how it ended; it writes no evidence. | "the cluster" when you mean any backend |
| Artifact store | The content-addressed store under `results/artifacts/` that keeps the files an experiment wrote, each under its SHA-256 hash. | "the sandbox" (that is disposable) |
| Artifact manifest | A run's list of the files it wrote, with path, size, and hash, including files not kept and why. | "the log" |
| Cleanup | The one documented command that deletes stored artifact files, dry run first, recording each deletion before making it. | deleting artifact files by hand |

## Study-specific terms (fill in when you fork)

> `<Define the intervention, the control condition, the outcome construct, and any instruments your study uses, so every document uses the same words for the same things.>`
