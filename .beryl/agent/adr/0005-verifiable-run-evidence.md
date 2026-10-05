# ADR 0005: Verifiable Run Evidence

## Status

Accepted on 2026-10-05 in the issue #9 design review (decision D2).

## Context

Issue #9 asks for append-only, content-addressed or equivalently verifiable logs and artifacts, and says runs cannot disappear from summaries. We had to decide what "immutable" means in practice. File permissions and write-once storage behave differently on laptops, Windows, and clusters, so they cannot be the guarantee.

## Decision

- **Append-only.** The harness only appends to the ledger and only creates logs and artifact manifests. It never edits or deletes them. The one deletion the harness performs is the artifact cleanup in [ADR 0006](0006-artifact-store-and-cleanup.md), which removes stored artifact files but never their records.
- **Hashes.** Every log and every stored artifact gets a SHA-256 hash. The ledger row records the hash of its log and of its artifact manifest, and the manifest records the hash of each file.
- **Hash chain.** Each ledger row stores the SHA-256 of the previous row's exact bytes. A verification command recomputes the chain and every recorded hash; a deleted, edited, or reordered row, or a changed log, fails verification.
- **Exact bytes.** Hashes cover the bytes as written, including line endings. Evidence files must never pass through Git line-ending conversion (#14).
- **Not included:** read-only file permissions and write-once storage.

## Consequences

- **Benefit:** anyone can prove that no run was removed or altered after it was recorded, on any platform, with the standard library alone.
- **Tradeoff:** the chain proves internal consistency only. Someone who rewrites every row from some point onward can produce a new consistent chain. Detecting that needs the latest row hash anchored outside the file, for example in a commit or in the reviewed run archives that issue #6 introduces (PR #18).
- **Follow-up:** the implementing PRs add the hash columns and the verification command, and update the ledger schema in `results/README.md`. Adding ledger columns changes the row that issue #6's `run-reference` archives, so coordinate the schema change with that work. A local ledger written before the change is reported as unchained up to its first chained row; old rows are never rewritten.
