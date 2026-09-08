# Statistical Analysis

This file is the pre-registered analysis plan. Fix it before data collection so the analysis is not chosen to fit the result. Keep it synchronized with the experiment design (`docs/05`), the `results/` templates, and the `analysis/` scripts.

## Hypotheses

> `<State the statistical hypotheses (null and alternative) that correspond to the research question and sub-questions.>`

## Primary analysis

> `<Name the test or model for the primary outcome metric, the comparison it makes, and the assumptions it rests on.>`

## Secondary and exploratory analyses

> `<List secondary analyses and clearly label anything exploratory.>`

## Power and sample size

> `<State the target effect size, alpha, power, and the resulting sample size. If simulation-based, describe it.>`

## Analysis implementation

The scripts in `analysis/` compute these statistics from the structured logs in `results/` once real data exists. They never fabricate data; they read only what the sandboxed runner or the researcher recorded.
