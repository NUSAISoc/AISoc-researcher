# Research workflow commands

The [approved contract](../docs/00-research-workflow-controls.md) defines the lifecycle and ownership rules. Python 3.11 or newer is sufficient. The manifest starts empty; tests use temporary repositories rather than inventing study evidence.

## Inspect and validate

```bash
python3 -m workflow check
python3 -m workflow manifest
python3 -m workflow rebuild
python3 -m workflow check --base origin/main
```

`check` verifies record metadata, exact provenance links, required decision targets, lifecycle states, committed run evidence archives, and manifest parity. `--base` also walks every retained revision between the Git base and the current record, checking stable identities, one-step revision increments, lifecycle rules, and a matching application receipt for each step. A record created on the branch may advance from its retained initial revision before merge. Rollback steps must match their referenced earlier receipt and restored content; supporting decisions still follow normal decision rules. Receipt filenames must match proposal digests and receipt content must agree with the proposal. It is structural validation, not authentication of a receipt's reviewer fields. The `Workflow record checks` CI job runs those checks. Live branch-protection configuration and human PR review remain externally owned acceptance controls; neither this job nor Beryl readiness proves those settings are enabled.

## Configure trusted human review

`workflow/policy.json` deliberately ships with empty `researchers`, `maintainers`, and `owners`. A maintainer must assign human GitHub usernames through ordinary protected-branch review before verified application is possible. `owners` maps each record's owner label to its authorized reviewer usernames. `repository` names the repository that receives the proposal PR. Forks must update that value through review. Do not infer a reviewer identity from a display name or from an agent-written approval field.

The CLI loads policy from `--trusted-base`, defaulting to `origin/main`, and rejects a different working-copy policy. The caller must designate an already reviewed Git revision from the integration branch; naming a locally authored commit is not an independent trust proof. Initial policy installation and later policy changes remain subject to ordinary maintainer/researcher review. No command configures GitHub branch protection or grants permissions.

## Prepare and review an edit

Create a JSON change-set file mapping repository-relative paths to exact replacement text. Record edits increment `revision` and retain their stable ID, type, and creation date. Type-specific evidence and decision links identify exact revisions. A new record starts in its initial state. Prepare proposed decision records first; when approving a hypothesis, approve its decision and the hypothesis in the same change set, with the decision targeting the hypothesis's new revision.

```bash
python3 -m workflow propose --changes change-set.json --author YOUR_NAME --reason "Explain the change and its evidence" --save
python3 -m workflow validate --proposal docs/workflow/proposals/PROPOSAL_DIGEST.json
```

Preparation saves a digest-named proposal and prints a unified diff. It does not mutate the proposed targets. Commit the proposal file on a review branch and open a PR in the configured repository using the ordinary contribution process. Assigned humans review the exact proposal commit. The workflow itself never creates PRs or submits reviews. Offline preparation/validation needs a local trusted Git base; verification of human approval needs the GitHub CLI and read access to reviews and the proposal content.

```bash
python3 -m workflow apply --proposal docs/workflow/proposals/PROPOSAL_DIGEST.json --pull-number PR_NUMBER
```

Application verifies the proposal in the PR's current head commit, the latest substantive human reviews, and all required roles. It rejects bot, self, stale, dismissed, or changed-proposal approvals. Network or credential errors leave the proposal pending. It then rechecks local input hashes, preserves earlier record revisions and a receipt, applies the file set under an exclusive lock, and regenerates the manifest. Committing or merging the resulting change remains governed by the repository's normal review policy.

The reviewed branch must also contain the same source snapshot that the proposal was prepared against. Changed, missing, or newly appearing source files invalidate that review. Keep the proposal review commit stable; applying its targets can be committed on a separate integration branch and reviewed under the ordinary protected-branch policy. Proposals larger than 1 MiB are refused because this adapter requires GitHub's base64 contents response.

Raw ledger/log writes, generated manifests/report outputs, generated instruction shims, and direct audit-history edits are refused. Existing study-content edits still require the complete synchronization and report-publication contract; approval of a text proposal does not establish semantic parity or publish generated artifacts. Run the full harness gate before committing any accepted change.

## Recovery and reviewed rollback

```bash
python3 -m workflow recover
python3 -m workflow rollback --digest APPLIED_PROPOSAL_DIGEST --author YOUR_NAME --reason "Explain the reversal" --save
```

Recovery restores the pre-application state after an interrupted transaction and refuses to overwrite subsequent edits. A committed transaction with a leftover journal is finalized without undoing it. Recovery inspects the process lock even when no transaction journal exists. It removes a confirmed dead owner's lock and reports that no writes needed recovery; a live, invalid, or uncertain owner keeps its lock. With a journal, it then recovers the transaction as before. Transaction state is temporary and must not be committed.

Rollback prepares another proposal and needs fresh review. It restores earlier content with incremented record revisions and an audit reference to the reversed proposal. It refuses to delete new records, rewrite completed run evidence, or overwrite later edits. Retire new records instead of deleting them. For approved content whose restored revision requires a fresh decision target, prepare an explicit replacement change set with that decision; do not reuse the old approval.

## Adapter contracts and limits

- `read_record(root, path)`, `build_manifest(root)`, and `validate_change(root, replacements)` provide shared read/validation contracts.
- `propose_change(root, replacements, author=..., reason=..., trusted_ref=...)` produces a pending exact proposal.
- `apply_approved_change(root, proposal, pull_number=..., trusted_ref=..., verifier=...)` accepts a proposal only through a trusted review adapter.
- `GitHubReviews(fetch=...)` is the external-system boundary. The default adapter only reads GitHub. Substitute it in deterministic tests, never accept an agent-supplied review JSON as an adapter.
- Evidence tools, the UI, the runner, and playbooks use the same IDs/revisions. The runner keeps its ledger/log authority and execution behavior. Governance does not reinterpret a failed run as a scientific refutation.

Approved campaigns include a protocol file hash, accepted evaluations include an analysis file hash, and terminal runs include configuration, ledger-row, and log hashes. Inspect local runner references without writing them:

```bash
python3 -m workflow run-reference --run-id EXISTING_RUN_ID
```

Before submitting a completed, failed, or executed cancelled run, prepare its evidence archive:

```bash
python3 -m workflow run-reference --run-id EXISTING_RUN_ID --archive
```

This read-only command returns `details` for the run record and a `changes` mapping containing the exact archive text. Add that mapping to the same change set as the terminal run and its approval decision. Do not pre-write the archive: it is included in the proposal diff and created by reviewed application. Commit the resulting record, archive, retained revisions, receipt, and manifest together. If the same archive is already retained, reuse its `evidence_ref` and omit its unchanged text from the change set.

Archives under `results/evidence/RUN_ID/SHA256.json` retain exactly one runner ledger row, its original ledger/log paths, and the exact UTF-8 log bytes (including line endings). Preparation refuses archives that differ from existing runner output. Archives are immutable and required for terminal records, including retained historical revisions. The original runtime outputs remain runner-owned and can be absent from a fresh checkout; available originals must agree with the archive. Remote approval snapshots bind the committed archive or its proposed text rather than ignored runtime logs or the mutable runtime ledger. Archive hashes verify integrity, while human review remains responsible for source authenticity and appropriate evidence disclosure. Existing terminal records without archives must have their original evidence retained before using this contract. The existing 1 MiB proposal limit applies to archive submissions too.

Current records must resolve current source artifacts exactly. Historical records can resolve retained source artifacts under `docs/workflow/history/artifacts/`. Drafts remain visible but are excluded from active research until their approval requirements are met. Reviewed rollback preserves approved decision records rather than restoring their earlier proposed status.

Retain records, receipts, and referenced Git history for the project lifetime and handover. Protect refs and backups operationally. Privileged local file edits can bypass a CLI; the current CI check is structural and normal human review is still required for authoritative acceptance. The workflow is not a cryptographic filesystem access-control mechanism.
