# Contributing to AISoc Researcher

Thank you for improving this autoresearch harness. Contributions should make the research process more reproducible, inspectable, and useful while preserving researcher control.

## Before you begin

Use an existing issue or open one with the closest issue form before starting substantial work. Small typo fixes may be submitted directly as pull requests. For design, governance, or behavior changes, state the problem, affected boundary, proposed outcome, and evidence needed for review before implementation.

We welcome these contribution types:

| Type | Examples | Required evidence | Maintainer review focus |
| --- | --- | --- | --- |
| Core harness | checks, control-plane scripts, sandbox behavior | deterministic checks and focused tests | backward compatibility, safety, and ownership boundaries |
| Documentation | research workflow, setup, or clarification | changed links and Markdown checks | canonical boundary and synchronization contract |
| Experiment adapter | a protocol integration or runner extension | offline or synthetic proof, ledger/log traceability | sandbox confinement, fail-closed live mode, and provenance |
| Playbook | reusable human-readable guidance | clear inputs, outputs, and scope | no hidden state or conflicting policy |
| Bug report | reproducible failure or regression | minimal reproduction and environment | scope, severity, and a protecting check |

## Local setup

Python 3.11 or newer is required. Fork the repository, then clone your fork and add the upstream remote if you want to pull updates:

```bash
git clone git@github.com:<your-account>/AISoc-researcher.git
cd AISoc-researcher
git remote add upstream git@github.com:NUSAISoc/AISoc-researcher.git
./.beryl/scripts/check.sh --development
python3 -m unittest discover -s tests -t .
```

Create a focused branch from the current `main`, for example `docs/contribution-guide` or `fix/ledger-validation`. Keep a branch to one reviewable purpose and do not commit generated experiment output, credentials, tokens, or participant-identifying data.

## Research integrity and reproducibility

Every contribution must preserve the rules in [RESEARCH_RULES.md](RESEARCH_RULES.md). In particular:

- Do not fabricate experimental data. Only the sandboxed runner may write run evidence, and every result must be traceable through `results/ledger.csv` and a run log.
- Keep live execution fail-closed when authorization or credentials are absent. Do not add secrets to the repository, issue, pull request, test fixture, or CI output.
- Keep experiment execution inside `experiments/` and `results/`; do not let an adapter mutate researcher-owned paths.
- Make research decisions at their canonical `docs/` boundary, then apply the complete [Synchronization Contract](.beryl/agent/synchronization-contract.md), including report artifacts when the change affects them.
- Do not add application code under `solution/` before the PRD is explicitly green-lit.

Fork pull requests are intentionally treated as untrusted. Maintainers must not expose repository secrets to forked code or ask contributors to provide credentials. Use the deterministic synthetic mode and redacted fixtures for review.

## Making a pull request

1. Rebase or merge the current `main` into your branch as appropriate.
2. Keep the change focused and update the relevant canonical documentation when a durable behavior or term changes.
3. Run the checks below and include their results in the pull request.
4. Use the pull-request template to identify scope, evidence, tests, compatibility, provenance, and integrity implications.
5. Respond to review feedback. A maintainer merges only after the required approval and status checks pass.

Run the narrowest relevant test first. Before requesting review, run:

```bash
./.beryl/scripts/check.sh --development
python3 -m unittest discover -s tests -t .
```

The protected `main` branch accepts ordinary changes only through a pull request with one approving review, the required `Research harness checks` status check, and resolved review conversations. See the version-controlled policy in [.github/branch-protection.md](.github/branch-protection.md).

## Generated artifacts and provenance

Do not hand-edit generated Word, PDF, hash, log, ledger, or analysis artifacts. When a research-content change requires report publication, regenerate it through the documented command and include the refreshed artifacts and hashes in the same pull request. Cite the source, protocol, issue, or authorization that establishes any new provenance claim. If a required artifact cannot be generated locally, explain why and ask a maintainer before merging.

## Review expectations

Be respectful, specific, and open to revision. Maintainers review correctness, research integrity, reproducibility, scope, and long-term maintainability. A change may be declined when it needs a clearer problem statement, a smaller scope, or evidence that its behavior is safe and reproducible.
