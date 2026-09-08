# Task Routing

Purpose: choose the smallest task workflow to load, and make every task get routed and verified against this repository's research standards. Do not load every workflow by default.

This is a **generalized autoresearch harness**, not an application repository (until the PRD is green-lit and the solution app is added as a submodule under `solution/`). Most work here is research writing, design, and running sandboxed experiments, so the routing table below adds research intents on top of the standard Beryl software intents.

## Routing Rule

1. Read [RESEARCH_RULES.md](../../RESEARCH_RULES.md), [synchronization-contract.md](synchronization-contract.md), and this file. For problem, solution, or improvement work, also read [systems-thinking-methodology.md](systems-thinking-methodology.md). Classify the user's current request.
2. If `.beryl/agent/hierarchy.md` exists, resume the active initial-build workflow before classifying a new request, unless the user explicitly asks to pause or abandon that build.
3. Load exactly one matching workflow skill from `.beryl/agent/skills/<skill-name>/SKILL.md`.
4. Load canonical project files only when that workflow asks for them.
5. If the task changes, re-route before continuing.
6. For non-trivial work with multiple viable paths, present the paths and wait for user approval unless the user explicitly allowed the agent to choose.

## Intent Map

| User Intent | Signals | Load |
| --- | --- | --- |
| Research writing | write/edit literature review, problem analysis, research question, solution design, experiment design, statistical analysis, evaluation, proposal, report, notes, references | `.beryl/agent/skills/academic-research-writer/SKILL.md` (then `voice-and-confidence-calibration` for user-facing surfaces; use `clearly-and-concisely-academic` for scholarly clarity) |
| User-facing polish | make the proposal/report/notes clearer, more engaging, more concise | `.beryl/agent/skills/voice-and-confidence-calibration/SKILL.md` |
| Scholarly clarity pass | tighten a paragraph, fix hedging, remove AI writing tells in academic prose | `.beryl/agent/skills/clearly-and-concisely-academic/SKILL.md` |
| Run or extend experiments | run the experiment, add an experiment, wire the sandbox runner, log results, analyse results | `.beryl/agent/skills/adding-features/SKILL.md` (with the Autoresearch Sandbox Gate below) |
| Planning | plan, design, approach, break this down | `.beryl/agent/skills/planning/SKILL.md` |
| Initial build (solution app, after green-light) | explicit request to build the application specified in `solution/PRD.md` | `.beryl/agent/skills/initial-build/SKILL.md` |
| Feature addition (in the solution submodule) | add, implement, build, create feature in the green-lit app | `.beryl/agent/skills/adding-features/SKILL.md` |
| Debugging | debug, bug, error, failing, broken, regression, test failure | `.beryl/agent/skills/debugging/SKILL.md` |
| Repository / codebase explanation | explain, walk me through, understand, where is this handled | `.beryl/agent/skills/explaining-codebase/SKILL.md` |

## Research Verification Gate

Every task that changes research content is verified against the harness standards before it is done:

1. **Synchronization contract.** Apply the complete target map in `synchronization-contract.md`. A change is incomplete if a shared fact is absent or contradictory in a required target, or if a report artifact or manifest is stale.
2. **Single research question.** After the change, the repository still states exactly one main research question, identically, everywhere it appears. If the change altered it, the update is universal (`ProjectProposal.md`, `docs/03-research-question.md`, `report/`, dependents).
3. **File synchronisation.** Information changed at its boundary in `docs/` is propagated to every named target, with superseded text deleted.
4. **No fabricated data.** `docs/06-experimental-results.md` and `results/` contain no invented numbers. Templates and headers only, until real data exists or is produced by the sandboxed runner and traced through `results/ledger.csv`.
5. **Green-light gate.** No application code exists under `solution/` unless the PRD was green-lit; before that, `solution/` holds `PRD.md` and planning documents only.
6. **Non-expert clarity.** The user-facing documents still let a non-expert name the independent variables, dependent variables, control condition, outcome metric, and experiment flow.
7. **Deterministic checks.** `./.beryl/scripts/check.sh` and `python3 -m unittest discover -s tests -t .` pass.

If any gate fails, the task is not done. Fix it before finishing.

## Autoresearch Sandbox Gate

Experiment work has extra requirements on top of the Research Verification Gate:

- The runner executes only inside a disposable workspace the repository creates under `experiments/workspaces/`. It never writes outside `experiments/` and `results/`, and never mutates any path the researcher owns.
- Synthetic mode is the default and needs no credentials or network. A live run is fail-closed: it requires an explicit dated authorization reference and configured credentials, and aborts (never silently falls back to synthetic) if they are absent.
- Every run appends exactly one row to `results/ledger.csv` and writes a result log under `results/logs/`. A result that is not traceable to a ledger row does not exist.
- The runner never fabricates data. Timeouts, refusals, and errors are recorded as results, not hidden.

## Feature Implementation Gate

Feature implementation (in the solution app, after green-light, or in the experiment harness) requires an approved plan.

- If the user asks for a feature and there is no approved plan, load `adding-features` and produce the plan first, then stop.
- Do not edit implementation code until the user ratifies the plan.
- After ratification, implement one internal feature slice at a time.
- Track feature-slice state internally in `.beryl/agent/session-state.md` only when needed; clear it when the feature is complete.

## Initial Build Routing Gate

- Use `initial-build` only when the user explicitly green-lights building the application specified in `solution/PRD.md`. Do not infer this route from research or writing tasks.
- The solution app is built as a **submodule** under `solution/`. Do not create it before the green-light.
- Present scope, hierarchy, dependencies, deliverables, checks, and implementation order for ratification before creating `.beryl/agent/hierarchy.md` or editing build code.

## Sub-Agent Policy

Do not use sub-agents unless the user explicitly asks for sub-agents, parallel agents, reviewer agents, or competing agent implementations. When the user does request them, prefer a research-appropriate split: for example a literature-review track, a design track, and an independent reviewer that audits the work against the Research Verification Gate above.

## Supporting Skill Escalation

- Use `grill-me` for structured critique before risky, ambiguous, or cross-cutting research-design decisions (a change to the research question, the outcome metric, or the analysis plan).
- Use `interview-me` only when `grill-me` leaves an unresolved decision that depends on user judgment and cannot be answered from the repository.
- Use `frontend-design` only inside the solution submodule, after green-light, for its UI.
- Do not use `interview-me` for routine task routing or discoverable repository facts.
