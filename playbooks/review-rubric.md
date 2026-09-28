# Playbook Review Rubric

The maintainer review layer for the community research-playbook registry. Use this
alongside the automated validator (`python3 playbooks/validate.py`) and the general
[maintainer review checklist](../.github/maintainer-review-checklist.md). The
validator enforces the machine-checkable rules in [SCHEMA.md](SCHEMA.md); this rubric
covers the judgment the validator cannot make.

## The boundary

A playbook is reusable, project-agnostic research guidance. It is not core policy, a
prompt template, code, or a one-off project-local note. Add a playbook by opening a
pull request that adds a file under `playbooks/entries/`; changes to the control
plane, the experiment harness, or a single project's own notes go through the normal
contribution path, not the registry.

## Checklist

- [ ] **In scope.** The submission is reusable research guidance, not core policy, a
  prompt template, code, or a one-off project-local note.
- [ ] **No hidden state.** A maintainer can review it from the file alone; it does not
  depend on undisclosed context, private data, or external state.
- [ ] **No conflicting policy.** It does not contradict the research rules, the
  synchronization contract, or another established playbook.
- [ ] **Honest evidence claim.** The `evidence_status` matches the actual support: an
  `established` playbook cites real work; an `experimental` one does not overclaim.
- [ ] **Not a duplicate.** It does not restate an existing playbook under a new id; a
  refinement of an existing one is a new version of that id, not a new id.
- [ ] **License and attribution present.** `license` and `authors` are filled and the
  content is the contributor's to license.
- [ ] **Complete.** All ten required body sections carry real content, and any
  `lifecycle_stages` name real research-lifecycle steps.

## Deprecation

Deprecating a playbook is an additive registry change, never a deletion: the version
file stays so prior adoptions remain reproducible. Record the reason and, where
applicable, the superseding version as an entry in `deprecations.json`; the file
itself is immutable and is never edited to mark it deprecated. Regenerate the index
(`python3 playbooks/validate.py --emit-index`) so the `deprecated` field is set.
