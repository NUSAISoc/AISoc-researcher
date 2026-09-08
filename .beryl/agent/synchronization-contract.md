# Synchronization Contract

This is a **completion gate**, not optional guidance. Before editing research content, read this contract with `RESEARCH_RULES.md`, the matching `docs/` boundary, and the matching workflow skill. A change is incomplete until every required target below is synchronized, generated artifacts are refreshed, and the deterministic checks pass.

## Authority and shared facts

`docs/` owns detailed research decisions. The following facts must agree wherever the named target states them: the active research question, the study domain and scope, the setting, the intervention or treatment, the control condition or baseline, the outcome metric, the timing of measurement, the no-fabricated-results status, and the PRD green-light boundary.

The files are not required to duplicate the same prose. They serve different readers. They are required to state the same shared facts without contradiction.

## Boundary map

| Change boundary | Canonical owner | Required synchronization targets |
| --- | --- | --- |
| Systems Thinking methodology, system objective, CLD, or SFD | `docs/02-problem-analysis.md` | `.beryl/agent/systems-thinking-methodology.md`, `docs/04-solution-design.md`, `docs/03-research-question.md` if objective framing changes, `references.md`, applicable `notes/`, `ProjectProposal.md`, report Markdown and LaTeX, then Word and PDF report artifacts |
| Literature, citations, or novelty | `docs/01-literature-review.md` | `references.md`, `readingList.md`, applicable `notes/`, `ProjectProposal.md`, report Markdown and LaTeX where the claim appears, then Word and PDF report artifacts |
| Problem or research question | `docs/02-problem-analysis.md` or `docs/03-research-question.md` | `RESEARCH_RULES.md`, `README.md`, `ProjectProposal.md`, `.beryl/agent/project-brief.md`, report Markdown and LaTeX, Word and PDF report artifacts, and every dependent plan |
| Solution or PRD requirement | `docs/04-solution-design.md` | `solution/PRD.md`, `ProjectProposal.md`, applicable `notes/`, report Markdown and LaTeX where summarized, then Word and PDF report artifacts |
| Experiment, measure, recruitment, or ethics | `docs/05-experiment-design.md` | `docs/07-statistical-analysis.md`, `docs/08-evaluation.md`, `results/` templates, `experiments/config.py` defaults where they encode the design, report appendix, `ProjectProposal.md`, report Markdown and LaTeX, then Word and PDF report artifacts |
| Analysis or evaluation | `docs/07-statistical-analysis.md` or `docs/08-evaluation.md` | `results/` templates, `analysis/`, report appendix, `ProjectProposal.md`, report Markdown and LaTeX, then Word and PDF report artifacts |
| Experiment harness or sandbox runner | `experiments/README.md` | `docs/05-experiment-design.md` where the protocol changes, `results/README.md` (log and ledger schema), `tests/`, `README.md` running-experiments section |
| Results after real data exists | `docs/06-experimental-results.md` | `results/`, `results/ledger.csv`, report Markdown and LaTeX, Word and PDF report artifacts, `ProjectProposal.md` only when its status or conclusion changes |

A conceptual diagram that models the study's own system follows the first row. An instrument diagram that the solution scores learners or agents against is solution-design content and follows the Solution or PRD requirement row, owned by `docs/04-solution-design.md`.

## Report publication chain

`report/report.md` and `report/report.tex` plus `report/sections/*.tex` are synchronized working representations. `report/report.docx` is regenerated from `report/report.md`; `report/report.pdf` is rendered from that Word file. Run:

```bash
bash report/build-pdf-from-docx.sh
```

The command refreshes `report/source.sha256` and `report/parity.sha256`. Do not hand-edit generated Word, PDF, or hash artifacts. A stale manifest is a failed synchronization gate. Until the report toolchain (`pandoc`, a LaTeX engine) is installed in your fork, keep the Markdown and LaTeX sources synchronized and generate the Word and PDF artifacts before publishing.

## Required completion review

Before reporting work complete, inspect the changed boundary and all named targets, delete superseded content, then run:

```bash
./.beryl/scripts/check.sh
python3 -m unittest discover -s tests -t .
```

If a shared fact changed, record the synchronization review in the commit message or a task verification record. Do not claim a generated report is current without refreshed hashes.
