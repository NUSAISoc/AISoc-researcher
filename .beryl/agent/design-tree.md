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

The harness lifecycle architecture is settled in [ADR 0003](adr/0003-research-workflow-controls.md): canonical readable records plus a generated manifest, exact revision links, externally verified human approval, retained revision/decision history, and reviewed immutable run evidence archives that remain verifiable in a fresh checkout. The complete contract is in [research workflow controls](../../docs/00-research-workflow-controls.md). This decision changes harness governance, not a fork's study design.

## Open Decisions (fill in when you fork)

- The one research question, its sub-questions, and the domain.
- The intervention, the control condition, and the outcome metric.
- The experiment protocol the sandboxed runner executes, and whether a live mode is needed.
- The instruments and the pre-registered analysis plan.
- Ethics/IRB process if the study involves human participants.
