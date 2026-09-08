# ADR 0002: CLD Case Naming and Learner-Model Log Shape

## Status

Accepted

## Context

The existing tutors build different diagrams in their two cases: systemsthinking-bot builds a causal loop diagram for the Borneo DDT "Fixes That Fail" case, and flubot builds a stock-and-flow diagram for the flu "Limits to Growth" case. The repository described both as stock-and-flow diagram construction. The learner-model design for the CLD case introduces a researcher-side diagram that the tutor scores against, per-sub-skill evidence levels, and a per-update trajectory record that a single session-log row cannot hold. The PRD used "answer key" only for the thing the tutor must never reveal, so the same words could not also name the scoring object.

## Decision

- Name each case by the diagram it builds: causal loop diagram (Borneo, systemsthinking-bot) and stock-and-flow diagram (flu, flubot). Prose that covers both says "live diagram construction".
- Call the researcher-side scoring diagram the reference CLD (and, for the flu case, the reference SFD). Retire "answer key" as a term.
- Rename the session-log field `sfd_action` to `diagram_action`, with the element type recorded in the value.
- Record the learner-model trajectory in its own template, `results/learner_model_trajectory.csv`, one row per sub-skill update, rather than as a collapsed column of `results/session_log.csv`.
- Keep the two diagram vocabularies apart: the conceptual learning-system CLD keeps its loops R1, B1, and R2; a case reference CLD keeps the course's own loop labels; prose always says which diagram a loop label belongs to.

## Consequences

- **Benefit:** The documents state which diagram each case builds, the scoring object has one name, and the log can hold one row per sub-skill update.
- **Tradeoff:** A field rename and a new template are decided before any application exists; both must be carried into the green-lit build.
- **Follow-up:** Linked from `.beryl/agent/design-tree.md`. The SFD case receives its own sub-skill set and reference SFD later, using the same structure.
