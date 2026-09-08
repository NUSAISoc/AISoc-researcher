# Project Proposal

This is the high-level statement of the study, written for a reader who wants the whole thing in a few pages. It is one of the three user-facing surfaces (with `report/` and `notes/`). Keep it engaging, concise, and limited to the main ideas. Write it with `academic-research-writer`, then pass it through `voice-and-confidence-calibration`.

This file ships as a fork template. Replace the placeholders with your study and keep the shared facts synchronized with `docs/` per the [Synchronization Contract](.beryl/agent/synchronization-contract.md).

## The question

> `<Your one main research question goes here.>`

This is the single main research question. It reads identically here, in `docs/03-research-question.md`, in `RESEARCH_RULES.md`, and everywhere else the synchronization contract names it.

## Why it matters

> `<A few sentences on the problem and why answering this question is worth doing. Ground it in the actual setting, not a generic description.>`

## What we compare

A non-expert should be able to finish this section and state the design without help.

- **Independent variable:** `<what is manipulated, e.g. condition = treatment vs control>`
- **Dependent variable / outcome metric:** `<what is measured>`
- **Control condition:** `<the baseline or existing solution>`
- **Experiment flow:** `<the steps a participant or subject goes through, and when the outcome is measured>`

## The proposed intervention

> `<One paragraph on the treatment and the mechanism it changes. The detail lives in docs/04-solution-design.md and solution/PRD.md.>`

## How the study runs

Experiments run automatically inside a sandbox this repository creates, and every run is logged and auditable. No result is ever fabricated; the results files stay empty until real data exists. The researcher stays in control of everything and can inspect or change any part by hand or with a prompt.

## Status

> `<Where the project is now: what is designed, what is pending, and whether the solution PRD has been green-lit.>`
