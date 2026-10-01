# Design & rationale — Research-Playbook Registry

This document explains *why* the registry is built the way it is, and gives a
newcomer (a reviewer, or someone picking up related work) a reading order. For
*how to use* the registry, see [`README.md`](README.md); for the exact file
contract, see [`SCHEMA.md`](SCHEMA.md).

## Where to start (reading order)

1. [`README.md`](README.md) — what the registry is, the three roles, and the
   registry-vs-normal-PR boundary.
2. [`SCHEMA.md`](SCHEMA.md) — the playbook file format, controlled vocabularies,
   versioning, and the immutability guarantee. This is the contract everything
   else is checked against.
3. [`entries/`](entries/) — the two seeded playbooks, concrete examples of the
   schema in practice.
4. [`validate.py`](validate.py) — the stdlib-only validator and index emitter
   that enforces the schema. The module docstring and the constants at the top
   (`EVIDENCE_STATUSES`, `REQUIRED_SECTIONS`, the regexes) are the rules at a
   glance.
5. [`../tests/test_playbook_registry.py`](../tests/test_playbook_registry.py) —
   the CI gate. The test names are the fastest way to learn the invariants.

## Objective

Let a wider community share reusable, evidence-aware research practices
("playbooks"), while every research project keeps the power to **inspect, pin,
override, and reproduce** the guidance it used — so a shared library never
silently changes a project's methodology underneath it. Adopting new guidance is
always a deliberate, recorded step.

## Locked design decisions

| # | Decision | Choice | Why |
|---|---|---|---|
| 1 | Trust model | Curated + lint + content-digest now, **signing-ready** | Reserve `publisher`/`key_id`/`signature` fields now (kept off in v1); a signing chain can be borrowed later with no format break. |
| 2 | Quality gate | Lint + maintainer rubric | Two layers: deterministic checks (`validate.py`, `tests/`) plus human review ([`review-rubric.md`](review-rubric.md)). Heavier moderation is deferred to v2. |
| 3 | File format | YAML frontmatter + Markdown | Human-writable headed Markdown plus a machine-readable header for lint and the generated index. |

Resolved open questions: SPEC is the single source of truth (other spec
artifacts became pointers); signing stays dormant (the registry is correct
regardless); `lifecycle_stages` is optional, may be empty, and each id must
exactly equal a `docs/NN-name.md` filename stem.

## The core idea (why immutability + pins)

A bad or drifting playbook would otherwise silently propagate into many
projects' methodology — a reinforcing loop. The balancing mechanism is
**immutable, digest-pinned published versions** plus **deliberate, undoable
pins**:

- One immutable file per version (`entries/<id>/<version>.md`). A published
  version is never edited after merge; new guidance = a new file + a new semver.
- `registry.json` is **generated** by `validate.py --emit-index`, never
  hand-edited; CI fails if the committed index differs from a fresh rebuild.
- A project records what it uses in its own `adoptions.json` (pin the version,
  the `content_sha256` at adoption time, the `influenced_decisions`, and any
  local `override`). Upgrading is a deliberate version + digest bump; rolling
  back restores the prior record. The old version file always exists, so
  reproduction is exact.

Drift becomes structurally impossible rather than policy-dependent. The gap
between "guidance improves" and "a project adopts it" is made explicit and
opt-in, never automatic.

## Scope boundary

The system boundary is the `playbooks/` shelf and its trust rules — **not**
`.beryl/` (the locked control plane), **not** contribution governance, **not**
lifecycle semantics. Playbooks live outside `.beryl/` because existing skills
sit under a locked component; playbooks need their own shelf. Nothing under
`.beryl/` is modified by this change.

## How the issue's acceptance criteria are met

| Acceptance criterion (issue #10) | Satisfied by |
|---|---|
| Add a valid playbook without altering the core control plane | New files only under `playbooks/entries/` (+ regenerated `registry.json`); the gate lives in `tests/`; `.beryl/` untouched. Entry files don't match the test manifest globs, so a contributor never trips the manifest gate. |
| Inspect a playbook's version, evidence status, limits, decisions it influenced | Frontmatter + `registry.json` + `adoptions.json`'s `influenced_decisions`. |
| Malformed/incompatible playbooks fail validation; upgrades never silently alter workflow | `validate.py` + the `tests/` gate; immutable digest-pinned versions; pins are deliberate edits. |
| Preserves researcher override; auditable correction/deprecation paths | `adoptions.json` `override` preserved verbatim; deprecation is an additive entry in `deprecations.json`, projected by `--emit-index` into the generated registry row (the immutable file is never edited); old versions are never deleted. |

## Known limitations (deferred to v2)

- The `compatibility` range is **parse-only** in v1: a playbook can declare a
  range no real harness satisfies and still pass.
- `evidence_status: established` requires only *non-empty* citations, not
  *resolvable* ones.
- Signing fields are reserved but inert.
