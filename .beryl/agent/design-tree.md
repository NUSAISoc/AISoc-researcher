# Design Tree

## Current Design Concept

This repository is a generalized, forkable autoresearch harness. It holds and enforces the plan for a study and runs experiments automatically inside a repository-created sandbox. The harness itself is the artifact for now; the solution application is built only after the PRD in `solution/PRD.md` is green-lit, as a submodule under `solution/`. A fork replaces the placeholders (research question, domain, existing solution, variables) with a specific study; the invariants below hold in every fork.

## Settled Decisions (harness invariants)

- One main research question at a time; changes propagate to every file that states it (`RESEARCH_RULES.md`).
- No fabricated data. `results/` and `docs/06-experimental-results.md` stay empty until real data exists or is produced by the sandboxed runner and traced through `results/ledger.csv` (`RESEARCH_RULES.md`).
- Experiments run automatically in a disposable sandbox under `experiments/workspaces/`; the runner writes results only under `experiments/` and `results/`, appends one ledger row per run, and is fail-closed on missing live authorization (`experiments/README.md`).
- The solution app is not built before green-light (`solution/README.md`).
- The human is at the centre: the researcher reads three user-facing surfaces, and every harness decision is inspectable and changeable by hand or by prompt (`RESEARCH_RULES.md`).
- Problem and solution work uses Meadows-informed Systems Thinking methodology; the intervention is a testable leverage hypothesis, not established evidence (`.beryl/agent/systems-thinking-methodology.md`).
- The synchronization contract is a high-priority completion gate mapping each research boundary to its mandatory targets and requiring refreshed report source and artifact hashes (`.beryl/agent/synchronization-contract.md`).
- The report PDF is rendered from the current Word report, with source and output hashes recorded in `report/parity.sha256` (`report/build-pdf-from-docx.sh`).

## Settled Decisions (issue #9 run evidence)

These were accepted on 2026-10-05 and are not yet implemented. The runner documentation describes current behaviour until each implementing PR lands.

- Every run attempt is recorded, including refusals before the experiment starts ([ADR 0004](adr/0004-record-every-refused-run.md)).
- Run evidence is append-only and verifiable through SHA-256 hashes and a hash-chained ledger ([ADR 0005](adr/0005-verifiable-run-evidence.md)).
- Experiment files are kept in a content-addressed store, and can be deleted only through a documented, dry-run-first cleanup that records every deletion ([ADR 0006](adr/0006-artifact-store-and-cleanup.md)).
- Every run has a time limit, 1 hour by default ([ADR 0007](adr/0007-default-run-time-limit.md)).
- The runner writes all evidence and a backend only executes; the local backend uses a child process ([ADR 0008](adr/0008-runner-and-execution-backend.md)).
- A started marker precedes every run, and a run whose process is known to be gone is recorded as `lost` ([ADR 0009](adr/0009-started-markers-and-lost-runs.md)).
- Final run statuses in the ledger: `ok`, `error`, `cancelled`, `refused`, `timeout`, `lost`.
- Implementation order: ledger lock, refusal records, time limit with killed-run records, artifact storage, cleanup command.

## Open Decisions (harness)

- **New campaign or new run (issue #9 D7).** Decided when campaigns are built, using issue #6's campaign record. Starting position: a new run keeps the protocol and analysis plan and changes only the seed, the replicate number, or the resources; any change to the hypothesis, protocol, control, measures, analysis plan, or stopping rule is a new campaign version.
- **Ledger statuses and the issue #6 run lifecycle.** PR #18 gives runs the lifecycle `planned`, `authorized`, `running`, then `completed`, `failed`, or `cancelled`. The mapping from the six ledger statuses has to be agreed with that work. In particular, `cancelled` there can mean cancelled before running, while in the ledger it means interrupted during execution.

## Open Decisions (fill in when you fork)

- The one research question, its sub-questions, and the domain.
- The intervention, the control condition, and the outcome metric.
- The experiment protocol the sandboxed runner executes, and whether a live mode is needed.
- The instruments and the pre-registered analysis plan.
- Ethics/IRB process if the study involves human participants.
