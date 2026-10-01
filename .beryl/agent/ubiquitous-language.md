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

## Workflow terms

| Workflow term | Definition |
| --- | --- |
| Lifecycle record | A readable canonical file with a stable ID, type, owner, revision, status, and exact provenance links. |
| Manifest | A deterministic generated index of current lifecycle records; never an independent source of research decisions. |
| Campaign | An approved experiment plan grouping runs that test specified hypothesis revisions. |
| Proposal | An inspectable exact change set with rationale, evidence, before hashes, and input snapshot; preparing it does not apply it. |
| Approval decision | A record explaining authorization; actual authority requires externally verified human review of the exact proposal. |
| Retirement | A disposition that removes an item from active work while retaining its lifecycle status and history. |
| Reviewed rollback | A newly approved revision restoring prior content while preserving the intervening audit trail. |

## Study-specific terms (fill in when you fork)

> `<Define the intervention, the control condition, the outcome construct, and any instruments your study uses, so every document uses the same words for the same things.>`
