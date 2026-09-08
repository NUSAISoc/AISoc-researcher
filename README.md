# AISoc Researcher

A generalized, forkable **autoresearch harness**. Fork it, drop in your research question, and you get a control plane that holds your whole research plan, keeps every file synchronized, runs experiments automatically inside a sandbox it creates, and keeps you (the human) at the centre with full observability. It is built for AI-assisted research where the literature review and problem analysis are done autonomously by the agent, but you direct, review, and override everything.

This repository ships as a **template with placeholders**, not a specific study. The invariants (one research question, no fabricated data, human-owned review) hold in every fork.

## What you get

- **A control plane (Beryl).** Your research standards become files, routing, and deterministic checks, so any agent working here is steered to the right workflow and its output is verified before you trust it. Pinned to `v0.1.0` (commit `a0f5f51fbd21cb629622978358756a157df47b0e`); provenance is in [docs/00-beryl-provenance.md](docs/00-beryl-provenance.md).
- **Writing and research-practice skills.** `academic-research-writer`, `voice-and-confidence-calibration`, and `clearly-and-concisely-academic`, installed under `.beryl/agent/skills/`, so the prose the agent produces is scholarly and calibrated rather than an over-confident AI draft.
- **A sandboxed experiment runner.** `experiments/` runs your experiment automatically inside a disposable workspace, logs every run deterministically, and appends an audit row to `results/ledger.csv`. Synthetic mode is the default and offline; live mode is fail-closed.
- **A full research scaffold.** An ordered `docs/` process, user-facing `ProjectProposal.md`, `report/`, and `notes/`, a source record in `references.md` and `readingList.md`, a `solution/` PRD behind a green-light gate, and `results/` templates that stay empty until real data exists.

## The question

This harness holds exactly one main research question at a time. In the template it is a placeholder:

> `<Your one main research question goes here.>`

When you fork, you replace that placeholder identically in every file the [Synchronization Contract](.beryl/agent/synchronization-contract.md) names. The harness tests fail if it is missing anywhere it is required, which is how the one-question invariant stays enforced.

## Setup

Python 3.11 or newer is required. Nothing else is needed for a synthetic run.

1. **Fork or clone** this repository.
2. **Verify the control plane and the harness:**

   ```bash
   ./.beryl/scripts/check.sh
   python3 -m unittest discover -s tests -t .
   ```

3. **Try the sandboxed runner** (deterministic, offline, no credentials):

   ```bash
   python3 -m experiments.run_experiment
   python3 -m analysis.summarize results/logs/<run_id>.jsonl
   ```

4. **Make it your study.** Replace the placeholders, in one unit of work per change, following the workflow below.

## Contributing

Contributions are welcome through focused fork-based pull requests. Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup, contribution types, reproducibility rules, verification, and review expectations. The required protected-branch settings are recorded in [.github/branch-protection.md](.github/branch-protection.md).

## The researcher workflow

1. **State your question.** Put your one research question into [docs/03-research-question.md](docs/03-research-question.md) and propagate it (identically) to every target the synchronization contract lists. Delete the placeholder everywhere.
2. **Let the agent review the literature and frame the problem.** Ask it to fill [docs/01-literature-review.md](docs/01-literature-review.md) and [docs/02-problem-analysis.md](docs/02-problem-analysis.md). It works autonomously here; you review. Problem framing uses the [Systems Thinking Methodology](.beryl/agent/systems-thinking-methodology.md).
3. **Design the intervention and the experiment.** Fill [docs/04-solution-design.md](docs/04-solution-design.md), [docs/05-experiment-design.md](docs/05-experiment-design.md), and the analysis plan in [docs/07-statistical-analysis.md](docs/07-statistical-analysis.md).
4. **Wire the experiment.** Replace the synthetic example in [experiments/experiment.py](experiments/experiment.py) with your protocol. Keep it inside the sandbox and never invent values. See [experiments/README.md](experiments/README.md).
5. **Run and analyse.** Run the sandboxed runner. Each run is logged and appears in the ledger. When you have real data, promote it into `results/` and `docs/06-experimental-results.md` (a deliberate, reviewed step) and analyse it with [analysis/](analysis/).
6. **Keep the write-up in lockstep.** As each step changes, update `ProjectProposal.md`, `report/`, and `notes/` in the same unit of work, then run the gate.

At every step you keep control. The three user-facing surfaces (`ProjectProposal.md`, `report/`, `notes/`) are written to be read by a human, and you can change anything by hand or by asking the agent.

## How tasks get routed and verified

Beryl is the control plane. When you give the agent a task, it reads [.beryl/agent/task-routing.md](.beryl/agent/task-routing.md), classifies the task, and loads exactly one workflow skill. Research writing loads `academic-research-writer`; the user-facing surfaces additionally get a `voice-and-confidence-calibration` pass; experiment work loads `adding-features` under the Autoresearch Sandbox Gate.

Every task that changes research content follows the [Synchronization Contract](.beryl/agent/synchronization-contract.md), then passes the Research Verification Gate in `task-routing.md`. Two commands enforce the mechanical parts:

```bash
./.beryl/scripts/check.sh
python3 -m unittest discover -s tests -t .
```

The first runs Beryl's deterministic gate (Markdown sanity, component integrity, secret scan, test-manifest integrity, and the affected tests). The second runs the harness tests, which encode the standards: required structure, the single-research-question invariant, the no-fabricated-data invariant, the green-light gate, and the sandbox's safety properties.

## The rules, in one paragraph

There is one main research question at a time; changing it is a universal update across every file that states it. Every change is made at the right file boundary and propagated to the other files that hold the same information, and superseded content is deleted so only the current version survives. No experimental result is ever fabricated; the results sheets and the results doc stay empty until real data exists, and the sandboxed runner is the only automatic writer of run output, always traceable through the ledger. The solution application is not built until you green-light the PRD, at which point it is added as a submodule under `solution/`. Occam's razor applies throughout. The full statement is in [RESEARCH_RULES.md](RESEARCH_RULES.md), and it is also stored as retrievable agent memory under [.beryl/agent/](.beryl/agent/).

## Repository map

| Location | Purpose |
| --- | --- |
| [ProjectProposal.md](ProjectProposal.md) | High-level statement of the study, linking to the detail. User-facing. |
| [report/](report/) | Living report (Markdown + LaTeX, with generated Word and PDF). User-facing, expert audience. |
| [notes/](notes/) | Short study explainers. User-facing. |
| [RESEARCH_RULES.md](RESEARCH_RULES.md) | The non-negotiable rules the harness enforces. |
| [readingList.md](readingList.md) | Forward reading queue: unread candidates. |
| [references.md](references.md) | Source index, split into current citations and all readings, with reading-depth tags. |
| [docs/](docs/) | Complete ordered research process, one file per step. |
| [solution/](solution/) | The PRD for the solution. The app is added here as a submodule only after green-light. |
| [experiments/](experiments/) | The sandboxed autoresearch runner. |
| [analysis/](analysis/) | Scripts that turn result logs into summaries and figures. |
| [results/](results/) | The run ledger, per-run logs, and empty data templates. No fabricated data, ever. |
| [tests/](tests/) | Harness tests that enforce the standards. |
| [.beryl/](.beryl/) | Beryl control plane: agent memory, task routing, and the deterministic check gate. |

## License

Beryl and this template are distributed under the terms in [LICENSE](LICENSE) and [NOTICE](NOTICE).
