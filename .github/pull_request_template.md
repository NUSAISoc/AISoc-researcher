## Summary

Describe the user-visible or maintainer-visible change and link the issue.

Closes #

## Contribution type

- [ ] Core harness
- [ ] Documentation
- [ ] Experiment adapter
- [ ] Playbook
- [ ] Bug fix

## Evidence and compatibility

- Problem/reproduction or design evidence:
- Backward-compatibility effect, or `Not applicable`:
- Provenance or authorization affected, or `Not applicable`:

## Research integrity

- [ ] No fabricated data, credentials, participant data, or unreviewed generated results are included.
- [ ] I considered the synchronization contract if this changes research content.
- [ ] Any experiment behavior remains sandbox-confined and live mode remains fail-closed.
- [ ] I did not add application code under `solution/` without an explicit PRD green-light.

## Verification

- [ ] `./.beryl/scripts/check.sh --development`
- [ ] `python3 -m unittest discover -s tests -t .`
- Narrow check and result:
- Checks unavailable or skipped, with reason:

## Reviewer notes

Call out changes to public behavior, generated artifacts, source provenance, or maintainer follow-up.
