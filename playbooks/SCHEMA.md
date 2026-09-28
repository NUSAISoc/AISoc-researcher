# Playbook Schema

This document is the contract for a community research playbook. It defines the
on-disk file format, the controlled vocabularies, the versioning policy, and the
immutability guarantee that `playbooks/validate.py` enforces.

A **playbook** is reusable, project-agnostic research guidance. It is not core
policy, a prompt template, code, or a one-off project-local note. See
[README.md](README.md) for the registry-vs-normal-contribution boundary.

## Intake and synchronization

The GitHub issue form `.github/ISSUE_TEMPLATE/playbook.yml` (fields: audience and
outcome; inputs, outputs, evidence, provenance, and no-hidden-state) is the
intake surface. This schema is a superset of those fields. The issue form, this
schema, `README.md`, the `CONTRIBUTING.md` Playbook row, the
`.github/maintainer-review-checklist.md`, and `review-rubric.md` all state one
shared boundary fact and must not contradict one another; any wording change
propagates to all of them in the same change (synchronization contract).

## File location

One immutable file per published version:

```
playbooks/entries/<id>/<version>.md
```

For example `playbooks/entries/fair-baseline-comparison/1.0.0.md`. The `<id>`
directory name must equal the `id` field, and the filename must equal
`<version>.md`.

## Frontmatter (machine-readable header)

```markdown
---
id: fair-baseline-comparison          # kebab-case, unique, stable across versions
version: 1.0.0                         # semver MAJOR.MINOR.PATCH
title: Fair Baseline Comparison
evidence_status: emerging              # controlled vocab, see below
lifecycle_stages: [05-experiment-design, 08-evaluation]   # OPTIONAL; each = a docs/NN-name.md stem
compatibility: ">=0.1.0"              # harness/domain compatibility range
authors: ["Jane Doe <jane@example.org>"]
license: CC-BY-4.0
citations:
  - "Author (Year). Title. Venue. DOI/URL."
# --- reserved for signing, OFF in v1 (validator accepts empty strings) ---
publisher: ""
key_id: ""
signature: ""
---
```

Required keys: `id`, `version`, `title`, `evidence_status`, `compatibility`,
`authors`, `license`, `citations`. Optional: `lifecycle_stages`. Reserved and
kept empty in v1: `publisher`, `key_id`, `signature`.

### lifecycle_stages

Optional. An empty list (or an omitted key) is valid. If present, every id must
exactly equal a `docs/NN-name.md` filename stem. The current valid stems are:

`00-beryl-provenance`, `01-literature-review`, `02-problem-analysis`,
`03-research-question`, `04-solution-design`, `05-experiment-design`,
`06-experimental-results`, `07-statistical-analysis`, `08-evaluation`.

## Required body sections

Every playbook body carries these ten headings, in order:

```markdown
## Purpose
## When to use (applicability conditions)
## Inputs
## Procedure
## Expected artifacts
## Failure modes
## Evidence and validation status
## Limitations
## Compatibility
## Citations
```

## Evidence-status vocabulary (controlled)

| Value | Meaning |
| --- | --- |
| `experimental` | Tried once or reasoned from first principles; not validated. |
| `emerging` | Used a few times with some supporting evidence; still provisional. |
| `established` | Repeatedly validated; safe default guidance. |
| `deprecated` | Superseded or found wrong; retained for provenance, not new use. |

`established` requires a non-empty `citations` list.

## Versioning (SemVer)

- PATCH: wording or clarity only.
- MINOR: additive (a new optional step or caveat) that does not invalidate prior use.
- MAJOR: the procedure changes such that the old and new versions yield materially
  different research decisions.

## Immutability

Once `entries/<id>/<version>.md` is merged, its content is frozen. The generated
`registry.json` records each entry's `content_sha256`; validation recomputes the
digest and fails on any edit to a published file. Changing guidance means
publishing a new version, never editing a released one. Digests are computed over
the file's content with line endings normalized to LF, so they are stable across
platforms.

## Compatibility

`compatibility` is a semver range naming the harness or domain baseline the
playbook assumes (for example `">=0.1.0"`). In v1 the validator checks only that
it parses; enforcement against a concrete harness version is deferred.

## Deprecation

Deprecating a playbook is additive; the version file is never deleted, so prior
adoptions stay reproducible. Because a published file is immutable, the
deprecation cannot be written into the file (that would break its digest).
Instead it is recorded in the hand-maintained ledger `playbooks/deprecations.json`:

```json
{
  "schemaVersion": 1,
  "deprecations": [
    {
      "id": "fair-baseline-comparison",
      "version": "1.0.0",
      "since": "2026-09-08",
      "reason": "Superseded by a stricter baseline procedure.",
      "superseded_by": "1.1.0"
    }
  ]
}
```

`id`, `version`, `since`, and `reason` are required strings; `superseded_by` is a
string or may be omitted/`null` (a playbook found wrong need not be superseded).
Each `(id, version)` must reference an existing entry, and each may be deprecated
once. `--emit-index` projects each ledger record into the matching
`registry.json` row's `deprecated` field; an entry with no ledger record has
`"deprecated": null`.

## The generated index

`playbooks/registry.json` is generated by `python3 playbooks/validate.py
--emit-index` and is never hand-edited. Its `deprecated` field is projected from
`deprecations.json` (see above), never written by hand. Published `(id, version)`
pairs are append-only. The validator recomputes the index from the entry files
and the ledger and fails on any mismatch — a digest change to a published file, a
hand-edit to the index (including a hand-set `deprecated` field that the ledger
does not back), or a single-sided add or removal (a file without its row, or a
row without its file). A coordinated deletion that removes both the file and its
row stays self-consistent, so it is guarded instead by the visible
`registry.json` diff at review time, the *deprecate, never delete* rule above,
human review, and Git history — history is never silently dropped. See
[README.md](README.md) for how a project pins, overrides, and reproduces the
guidance it adopts via `adoptions.example.json`.
