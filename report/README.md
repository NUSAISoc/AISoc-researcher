# Living Study Report

This directory holds the study's report. It is a living document: it is updated as the research progresses, alongside `ProjectProposal.md` and `docs/`, rather than written once at the end. It is the expert-facing surface, so it follows the knowledge-creation framework the field expects (grounded question, literature-derived hypotheses, a controlled design, a pre-registered analysis, and threats to validity).

The Word document is the publication source for the accompanying PDF. `build-pdf-from-docx.sh` regenerates `report.docx` from `report.md`, then renders `report.pdf` from that Word file. It writes `source.sha256` for the Markdown and LaTeX working sources plus `parity.sha256` for the Word and PDF artifacts. The [Synchronization Contract](../.beryl/agent/synchronization-contract.md) makes this publication chain mandatory after a report-related change. The build needs `pandoc` and a PDF engine (e.g. `tectonic`); until those are installed in your fork, keep the Markdown and LaTeX sources synchronized and generate the artifacts before publishing.

## Structure

```
report/
  report.md              maintained Markdown body (publication source for Word)
  report.tex             maintained LaTeX working representation
  build-pdf-from-docx.sh PDF renderer and parity-hash writer
  source.sha256          hashes of current Markdown and LaTeX working sources
  sections/
    introduction.tex     problem, gap, and research question
    method.tex           design, variables, control, outcome metric, analysis plan
    results.tex          results placeholder; stays empty until real data exists
  figures/               figures generated from real results data (empty until then)
```

## Rebuild

```bash
./build-pdf-from-docx.sh
```

## Rules

- Update the report when a research step changes, in the same unit of work as the `docs/` change. Keep exactly one current version.
- The results section stays empty of findings until real data exists. No fabricated results, ever.
- No em-dashes. Keep each prose paragraph on one physical source line.
