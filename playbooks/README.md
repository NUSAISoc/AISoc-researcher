# Community Research-Playbook Registry

This registry lets a wider community share reusable, evidence-aware research
practices ("playbooks"), while every research project keeps the power to
inspect, pin, override, and reproduce the guidance it used. A shared library
never silently changes a project's methodology underneath it: adopting new
guidance is always a deliberate, recorded step.

## Who uses it

- **Contributor** submits a playbook (a reusable, project-agnostic research
  recipe) by adding a file under `playbooks/entries/`, without touching the
  locked control plane.
- **Researcher / adopting project** pins a specific playbook version, records
  which decisions it influenced, overrides it locally, and reproduces exactly
  what was used.
- **Maintainer** runs the automated validator plus a written rubric to keep
  low-quality, duplicated, or misleading practices out, and deprecates without
  rewriting history.

## The boundary

A playbook is reusable, project-agnostic research guidance. It is not core
policy, a prompt template, code, or a one-off project-local note. Add a playbook
by opening a pull request that adds a file under `playbooks/entries/`; changes to
the control plane, the experiment harness, or a single project's own notes go
through the normal contribution path, not the registry.

## Files

- [`DESIGN.md`](DESIGN.md): the design rationale and a reading order for
  newcomers — why immutability + pins, the scope boundary, and how the issue's
  acceptance criteria are met.
- [`SCHEMA.md`](SCHEMA.md): the playbook file format, controlled vocabularies,
  versioning, and the immutability guarantee.
- `validate.py`: the stdlib-only validator and index emitter.
- `entries/<id>/<version>.md`: one immutable file per published version.
- `registry.json`: the generated index (never hand-edited).
- `deprecations.json`: the hand-maintained deprecation ledger; `--emit-index`
  projects it into the index's `deprecated` field (see [`SCHEMA.md`](SCHEMA.md)).
- [`adoptions.example.json`](adoptions.example.json): a copy-me template for how a
  project pins, overrides, and records a playbook's influence.
- [`review-rubric.md`](review-rubric.md): the maintainer review checklist for playbooks.

## Adding a playbook

1. Create `playbooks/entries/<id>/<version>.md` following [`SCHEMA.md`](SCHEMA.md).
2. Run `python3 playbooks/validate.py` to check it.
3. Run `python3 playbooks/validate.py --emit-index` to regenerate `registry.json`.
4. Commit the entry file and the regenerated index together, and open a pull request.

## Adopting a playbook in a project

Copy [`adoptions.example.json`](adoptions.example.json) to `playbooks/adoptions.json`
in your project and record each playbook you use: its `id`, the pinned `version`,
the `content_sha256` at adoption time, the decisions it `influenced_decisions`, and
any local `override`. To upgrade, bump the version and digest deliberately; to roll
back, restore the prior record. The old version file always exists, so reproduction
is exact.
