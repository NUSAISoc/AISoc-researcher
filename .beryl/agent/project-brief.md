# Project Brief

## What This Repository Is

This is a **generalized, forkable autoresearch harness**: a research-management and reproducibility control plane, not (yet) an application. It holds the full plan for a study, from literature review through experiment design and analysis, and it enforces the format that plan must keep. It also runs experiments automatically inside a repository-created sandbox and logs every run deterministically, so the research process and its evidence stay reproducible and human-owned.

Fork it, replace the placeholders with your own study, and the control plane keeps the project synchronized, honest about data, and readable by a human at every step.

The authoritative human-facing statement is [ProjectProposal.md](../../ProjectProposal.md). The non-negotiable rules are in [RESEARCH_RULES.md](../../RESEARCH_RULES.md), the [Synchronization Contract](synchronization-contract.md) is a completion gate for every research-content edit, and the [Systems Thinking Methodology](systems-thinking-methodology.md) governs problem and solution work. Read the applicable contracts before making substantive changes. The complete, ordered research process lives under [docs/](../../docs/).

## The One Research Question

> `<Your one main research question goes here.>`

There is exactly one main research question at any time. Changing it is a universal update across `ProjectProposal.md`, `docs/03-research-question.md`, `report/`, and every dependent file. The superseded version is deleted from those files (dated `docs/` records keep the audit trail).

## Prior Solution Being Improved On

> `<NAME THE EXISTING SOLUTION OR BASELINE your study improves on or compares against, with a one-paragraph description and a link. If the study is not comparative, state the status quo it is measured against. This is the control condition.>`

## Hard Boundaries

- **Do not build the solution artifact until the researcher green-lights the PRD.** The PRD lives in `solution/PRD.md`. Once green-lit, the app is added as a **submodule** in `solution/`. Remember this until the app becomes ready to build.
- **Never fabricate experimental data.** `docs/06-experimental-results.md` and the `results/` sheets stay empty until real, user-provided or pipeline-ingested data exists. The sandboxed runner in `experiments/` is the only automatic writer of results, and every run it produces is traceable through `results/ledger.csv`. No fake numbers, ever.
- One research question at a time; changes propagate to every file holding that information; superseded content is deleted.
- The human is at the centre. Keep everything the researcher would want to see in plain, readable, changeable files.

## User-Facing vs Workspace

The user reads only three things: `ProjectProposal.md`, `report/`, and `notes/`. These must be well written (engaging, concise, main ideas only) using `academic-research-writer` then `voice-and-confidence-calibration`. Everything else (`docs/`, `experiments/`, `analysis/`, `results/`, `solution/`, `tests/`, `.beryl/`) is the working space for detailed logs and process.

## Primary Workflows

1. **Change a step of the research process** (literature review, problem analysis, research question, solution design, experiment design, statistical analysis, evaluation): edit the matching `docs/` file at its boundary, then propagate to `ProjectProposal.md`, `report/`, and `notes/` where they hold the same information. Delete superseded text.
2. **Add or update a source**: record it in `references.md` (correct section, reading-depth tag), write full notes in `notes/`, and keep `readingList.md` as the forward queue only.
3. **Write or revise the PRD**: edit `solution/PRD.md`. Do not scaffold the app until green-light.
4. **Design or revise the experiment**: keep independent variables, dependent variables, control condition, outcome metric, experiment flow, and statistical analysis explicit and mutually consistent across `docs/05-experiment-design.md`, `docs/07-statistical-analysis.md`, `results/`, and the proposal.
5. **Run experiments**: use the sandboxed runner in `experiments/`. It executes automatically inside a disposable workspace the repository creates, writes a deterministic result log to `results/`, appends a ledger row, and never touches anything outside its sandbox. Real runs are fail-closed on missing authorization or configuration; there is no silent fabrication.

## Definition Of Done

A unit of work is complete only when:

1. The matching `docs/` file is updated, every target named in `synchronization-contract.md` is synced, report artifacts and hashes are refreshed where applicable, and superseded content is deleted.
2. `./.beryl/scripts/check.sh` passes.
3. `python3 -m unittest discover -s tests -t .` passes; harness tests still enforce structure, single-research-question, no-fabricated-data, and file-sync invariants.
4. User-facing documents changed in the unit were passed through `academic-research-writer` and `voice-and-confidence-calibration`.
5. A descriptive commit is made and pushed. Work is committed per unit, not batched per session.
