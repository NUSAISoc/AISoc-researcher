# Protected `main` policy

This file records the required GitHub configuration for the default branch. It is a human-readable record of the live setting, not a replacement for GitHub enforcement.

| Setting | Required value | Purpose |
| --- | --- | --- |
| Protected branch | `main` | Keeps the integration branch governed consistently. |
| Require a pull request before merging | Enabled | Ordinary changes cannot be pushed directly. |
| Required approving reviews | 1 | A second person reviews scope, evidence, and integrity. |
| Dismiss stale approvals | Enabled | Review applies to the current change. |
| Require status checks | `Research harness checks` | The deterministic gate and harness tests must pass. |
| Require branches to be up to date | Enabled | The check result applies to the merge result. |
| Require conversation resolution | Enabled | Review concerns are explicitly addressed. |
| Include administrators | Enabled | Maintainers follow the same ordinary-change control. |
| Allow force pushes or deletions | Disabled | Preserves auditable history. |
| Restrict who can push | Not configured | Open-source contributors use fork pull requests; merge authority remains with maintainers. |

Emergency changes should be exceptional, documented in the resulting pull request or issue, and followed by the same verification and review record as soon as practical. Do not bypass the research-integrity rules, provenance requirements, or no-fabricated-data rule.
