# Maintainer review checklist

Use this checklist for every pull request before merging into `main`.

## Scope and governance

- [ ] The pull request has a clear issue, purpose, and bounded scope.
- [ ] The contribution type has the evidence required by [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] The contributor has not included secrets, credentials, personal data, or unreviewed generated output.
- [ ] Backward-compatibility and migration effects are stated or explicitly not applicable.

## Reproducibility and research integrity

- [ ] The change preserves the one-research-question, no-fabricated-data, and PRD green-light invariants.
- [ ] An experiment adapter remains sandbox-confined, records a ledger row and log for each run, and fails closed for unauthorized live execution.
- [ ] Documentation changes were made at the canonical boundary and all synchronization targets were considered.
- [ ] Any provenance, authorization, source, or generated-artifact claim is traceable and reproducible.

## Verification and merge

- [ ] The narrow relevant check and the full deterministic gate passed.
- [ ] Python harness tests passed, or an unavailable check is explained and accepted.
- [ ] Tests were not weakened; intentional test and manifest changes have a stated rationale.
- [ ] Required GitHub status checks are green, review conversations are resolved, and one approving review is present.
- [ ] The branch-protection policy remains enabled and the merge method preserves a readable history.
