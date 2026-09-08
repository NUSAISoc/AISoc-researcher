# Architecture

This repository is a research harness, not an application. Its "architecture" is the set of file boundaries the harness enforces plus the sandboxed experiment pipeline, not a set of application modules. The solution application gets its own architecture once it is green-lit and added as a submodule under `solution/`.

## Boundaries (where information lives)

| Boundary | Owns | Does not own |
| --- | --- | --- |
| `docs/` | The complete, ordered research process, one file per step. The authoritative detail. | User-facing framing (that is the proposal, report, notes). |
| `ProjectProposal.md`, `report/`, `notes/` | The user-facing surfaces: high-level, formal, and explanatory views of the same research. `report/report.docx` is the publication source for the accompanying PDF, with hashes in `report/parity.sha256`. | New research decisions; those are made in `docs/` first, then propagated here. |
| `references.md`, `readingList.md`, `notes/` | The source record: index, forward queue, and full per-source detail. | (kept in sync with `docs/01-literature-review.md`). |
| `solution/` | The PRD for the solution, and later the solution app as a submodule. | Application code before green-light. |
| `experiments/` | The sandboxed autoresearch pipeline: runner, config, disposable workspaces, and the ledger writer. Executes experiments automatically and reproducibly. | Research narrative or fabricated data. |
| `analysis/` | Scripts that turn structured result logs into summary statistics and figures. | Raw run capture (that is `experiments/` and `results/`). |
| `results/` | Structured result logs, the run ledger, and empty data templates. | Any fabricated data. |
| `tests/` | Harness tests enforcing the standards. | Application tests (those live in the submodule). |
| `.beryl/` | The control plane: agent memory, routing, and the deterministic gate. | Research content; it references it but does not hold it. |

## The autoresearch pipeline

`experiments/run_experiment.py` is the single entry point. It reads `experiments/config.py`, creates a disposable sandbox under `experiments/workspaces/`, runs the configured experiment inside that sandbox, writes a JSON Lines result log under `results/logs/`, appends one row to `results/ledger.csv`, and (when `analysis/` is wired) regenerates summary figures. Synthetic mode is the default and is deterministic and offline; a live mode is fail-closed on missing authorization or credentials and never falls back to synthetic silently. The runner never writes outside `experiments/` and `results/`.

## Synchronisation rule

A change is made at its correct boundary in `docs/` and propagated to the other files that hold the same information (`ProjectProposal.md`, `report/`, `notes/`, `solution/`, `results/`, and the experiment config where it encodes the design), with superseded content deleted. `.beryl/agent/synchronization-contract.md` is the authoritative target map and publication-chain contract; `.beryl/agent/systems-thinking-methodology.md` is the required method for problem and solution work. The Research Verification Gate and deterministic harness tests enforce both.
