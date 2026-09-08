# Experiment Design

This file is the canonical owner of the experiment protocol. Keep it synchronized with the statistical analysis (`docs/07`), the evaluation (`docs/08`), the `results/` templates, and the experiment config in `experiments/config.py` where it encodes the design. A non-expert reading the user-facing documents must be able to state the independent variables, dependent variables, control condition, outcome metric, and experiment flow from this design.

## Variables

- **Independent variable(s):** `<what you manipulate; e.g. condition = treatment vs control>`
- **Dependent variable(s):** `<what you measure; the outcome metric>`
- **Controlled variables:** `<what you hold constant across conditions>`

## Conditions

- **Treatment:** `<the intervention from docs/04>`
- **Control:** `<the baseline / existing solution>`

## Participants or subjects

> `<If human participants: population, recruitment, sample size target, consent, anonymisation, and withdrawal. If agents or simulated subjects: the population and how it is sampled. Ethics belongs here, not as an afterthought.>`

## Procedure and flow

> `<Describe the experiment flow step by step, so a non-expert can follow it. Include the timing of measurement (e.g. pre vs post).>`

## Outcome metric

> `<Define the primary outcome metric precisely, and any secondary measures. This is the dependent variable the analysis compares between conditions.>`

## Automated execution

The sandboxed runner in `experiments/` executes this protocol automatically inside a disposable workspace and records every run in `results/ledger.csv`. Synthetic mode is the default; a live run is fail-closed on missing authorization or credentials. See `experiments/README.md`. The runner never fabricates data.
