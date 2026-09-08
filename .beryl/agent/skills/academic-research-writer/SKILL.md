# Academic Research Writer

## Purpose

Write academic research documents (literature reviews, protocols, reports, proposals) with scholarly standards, verified peer-reviewed sources, and consistent citations. Source: adapted from `endigo/claude-skills` `academic-research-writer` (buildwithclaude.com/skill/academic-research-writer, MIT). This copy is the repository-owned version; treat it as the source of truth in this project.

## Use When

- Writing or editing any document under `docs/`, `report/`, `notes/`, `ProjectProposal.md`, or `solution/`.
- Adding or verifying a source in `references.md` or `readingList.md`.

## Core Principles

- Academic rigor: follow scholarly conventions and maintain objectivity.
- Source verification: use peer-reviewed, credible sources; mark reading depth (`[full]`, `[abstract]`, `[artifact]`, `[non-peer-reviewed]`) exactly as `references.md` requires.
- Proper citation: every factual claim from an external source carries a citation.
- Research integrity: never fabricate results, quotes, page numbers, or statistics. All experimental data must be user-entered or ingested from a user-set-up pipeline.

## Workflow

1. Clarify the document type, scope, target reader (expert vs non-expert), and required sections.
2. Plan the research: research questions, search terms, databases (Google Scholar, arXiv, ACM DL, ScienceDirect, IEEE Xplore, PubMed, System Dynamics Review).
3. Discover and verify sources. For each: peer-reviewed venue, author affiliation, venue reputation, methodology soundness, relevance. Flag preprints, blogs, and vendor posts. Record every read source in `references.md` and its full notes under `notes/`.
4. Structure the document to the standard for its type (see below).
5. Write in the required voice. User-facing documents (ProjectProposal, report, notes) additionally follow `voice-and-confidence-calibration`.
6. Generate a consistent reference list. This project uses author-year in-text citation with a numbered `references.md` index; keep in-text citations and the index in sync.
7. Quality-assure: clear research question, logical flow, adequate source coverage, claims cited, limitations acknowledged, references consistent.

## Document Structures

- **Research report / paper**: Title, Abstract, Introduction (background, problem, objectives, contribution), Related Work / Literature Review, Method (design, data collection, analysis), Results, Discussion (interpretation, implications, limitations), Conclusion (summary, future work), References.
- **Literature review**: Title, Introduction, Review method, Thematic sections, Synthesis, Conclusion, References.
- **Protocol / experiment design**: Research question, hypotheses, variables (independent, dependent, controls), participants and recruitment, procedure/flow, measures, analysis plan, threats to validity.

## Output Formats

- Working documents under `docs/`, `notes/`: Markdown.
- The living report under `report/`: LaTeX source (`report.tex`) plus a generated PDF and a Word (`.docx`) version, with figures and a separate Appendix document.
- Keep each prose paragraph on one physical source line (no hard wrapping), matching the repository convention.

## Rules Specific To This Repository

- One main research question at a time. If a change touches it, make a universal update across `ProjectProposal.md`, `docs/03-research-question.md`, `report/`, and any dependent file.
- When information changes, delete the superseded version. Only the most current version is preserved. Dated decision records under `docs/` are the exception: they preserve superseded decisions as an audit trail.
- Never invent experimental results. `docs/06-experimental-results.md` and `results/` templates stay empty until real, user-provided data exists.
- Immediately upon reading the user-facing documents, a non-expert must be able to state the independent variables, dependent variables, control group, outcome metric (pre vs post), and experiment flow.
