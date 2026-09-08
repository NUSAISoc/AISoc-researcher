# Research Rules

These rules govern every change to this repository. They are the non-negotiable contract for any human or agent working here. This file plays the role that `AGENTS.md` plays in some sibling harnesses; the root `AGENTS.md` here is a Beryl-generated tool shim and must not be hand-edited. The primary human-facing statement of the study is [ProjectProposal.md](ProjectProposal.md); the complete ordered process is in [docs/](docs/).

This repository is a **generalized, forkable autoresearch harness**. It ships with placeholders, not a specific study. When you fork it, you replace the placeholders (the research question, the domain, the existing solution, the variables) with your own, and the rules below keep your project honest as it grows.

## The One Research Question

> `<Your one main research question goes here.>`

Replace the placeholder above with your study's single main research question, identically in every file the synchronization contract lists for the research question.

There is exactly one main research question at a time. If a change touches it, make a **universal update**: change it in `ProjectProposal.md`, `docs/03-research-question.md`, `report/`, `.beryl/agent/project-brief.md`, and every file that states or depends on it, in the same unit of work. Do not leave two research questions in the repository. The harness test suite fails if the canonical question is missing from a file that is required to state it.

## Non-Negotiable Research-Integrity Constraints

- **No fabricated data, ever.** No experimental result, participant response, score, measurement, or statistic may be invented. `docs/06-experimental-results.md` and every sheet in `results/` stay empty (headers and templates only) until real data is entered by the user or ingested from a pipeline the user set up, including the sandboxed experiment runner in `experiments/`. A placeholder number is a fabrication.
- **The autoresearch loop is auditable and human-owned.** Experiments run automatically inside the sandbox the repository creates (`experiments/`), but every run writes a deterministic record to `results/` and appends one row to `results/ledger.csv`. A result that cannot be traced to a ledger row and a run log does not exist. The human can inspect, re-run, or discard any run.
- **Do not build the solution artifact before green-light.** The proposed solution is specified in `solution/PRD.md`. No application code is written under `solution/` until the researcher green-lights that PRD. When green-lit, the app is added as a **submodule** under `solution/`.
- **One current version of everything.** When information changes, delete the superseded version from the working and user-facing files. Only the most updated version is preserved. The single exception is dated decision records under `docs/` (e.g. `docs/00-*`, direction amendments), which preserve superseded decisions as an audit trail.
- **Occam's razor.** Keep the design, the constraint set, the variable set, and the analysis as simple as possible without oversimplifying. A new construct, arm, or measure must be justified against a simpler alternative.

## Highest-Priority Synchronization Gate

Before any research-content edit, read and follow the Beryl [Synchronization Contract](.beryl/agent/synchronization-contract.md). It is a completion gate: every shared research fact must be propagated to the targets named for its boundary, and report Markdown, LaTeX, Word, and PDF artifacts must be regenerated through the documented publication chain. Distinct documents may use different prose for different readers, but they must not contradict one another. A change that skips a required target, leaves a stale report manifest, or preserves superseded content is incomplete.

## Systems Thinking Methodology Gate

For problem identification, solution design, and any proposed improvement, read and apply [.beryl/agent/systems-thinking-methodology.md](.beryl/agent/systems-thinking-methodology.md). Define the research objective, system boundary, actors, feedback structure, delays, assumptions, and leverage hypothesis before proposing an intervention. Use a conceptual Causal Loop Diagram (CLD) or, only when stocks and flows are defined without invented quantities, a Stock and Flow Diagram (SFD). Diagrams are theory-informed models, never experimental evidence or fabricated results.

## Human-at-the-Centre Rule

The human researcher is the control point for everything, with full observability.

- The user reads only three surfaces: `ProjectProposal.md`, `report/`, and `notes/`. Keep these engaging, concise, and limited to the main ideas. Everything else is the working space.
- Anything the harness decides or produces must be inspectable in plain, readable material and changeable either by hand or with a single prompt. Do not hide state the researcher would want to see.
- The literature review and problem-space analysis are done autonomously by the agent; the human directs, reviews, and overrides. Nothing the agent concludes is treated as settled until it survives the verification gate and the researcher's review.

## File-Boundary and Synchronisation Rules

- Every change edits information at its correct boundary. The authoritative boundary map and generated-report workflow are in `.beryl/agent/synchronization-contract.md`; follow its complete target list rather than a partial local interpretation.
- A non-expert reading the user-facing documents must be able to state, without help, the independent variables, dependent variables, control condition, outcome metric, and experiment flow. An expert reading `report/` must see a correct knowledge-creation framework for the field (grounded research question, literature-derived hypotheses, a controlled design, a pre-registered analysis, and threats to validity).

## Writing Rules

- Use `academic-research-writer` for all research documents, then `voice-and-confidence-calibration` for the three user-facing surfaces (`ProjectProposal.md`, `report/`, `notes/`). Use `clearly-and-concisely-academic` for scholarly clarity in any prose.
- Maintain all sources in `references.md`, split into **Relevant Citations for the Current Research** and **All Readings Read So Far**, with reading-depth tags (`[full]`, `[abstract]`, `[artifact]`, `[non-peer-reviewed]`). Keep unread candidates in `readingList.md`. Keep full per-source detail in `notes/`.
- No em-dashes in any research prose. Keep each prose paragraph on one physical source line.

## Ethics and Human-Subjects Rules

- If the study involves human participants, recruitment, consent, anonymisation, and the option to withdraw are part of the design in `docs/05-experiment-design.md`, not an afterthought.
- No participant-identifying data is committed. `results/` holds anonymised, coded data only.

## Verification and Commit Discipline

- Run `./.beryl/scripts/check.sh` before every commit and fix what it reports.
- Run `python3 -m unittest discover -s tests -t .`; the harness tests enforce repository structure, the single-research-question invariant, the no-fabricated-results invariant, and file synchronisation.
- Commit after every discrete unit of work with a descriptive message, and push regularly. Do not batch a whole session into one commit.
- Do not weaken a harness test to make a change pass. If a test must change because the standard changed, run `./.beryl/scripts/update-test-manifest.sh` and explain why.
