# ADR 0006: Artifact Store and Documented Cleanup

## Status

Accepted on 2026-10-05 in the issue #9 design review (decision D3), with the researcher's condition that the cleanup procedure is clear to the user.

## Context

The runner deletes the sandbox after every run, so files an experiment writes are lost and only the log survives. Issue #9 asks for verifiable artifacts and a documented way to reduce storage without making recorded provenance ambiguous.

## Decision

**Keeping artifacts**

- After a run ends, whatever its status, the runner moves the files the experiment wrote out of the sandbox into a store under `results/artifacts/`. Each file is saved under its SHA-256 hash, so identical files are stored once. The store is local runtime state and is gitignored, like `results/logs/`.
- Each run gets an artifact manifest listing every file it wrote: relative path, size, and hash. The manifest also lists files that were not kept and why, so their absence is explained too.
- A `tmp/` folder inside the sandbox is not kept.
- Each run has a size limit. What happens to files beyond the limit is specified in the implementing PR, and is always recorded in the manifest, never silent.
- Ledger rows, logs, and manifests are kept forever. Only stored artifact files can ever be deleted.

**Cleanup, made clear to the user**

- There is exactly one way to delete stored artifacts: a cleanup command, documented in `experiments/README.md` under "Freeing space" with a worked example, and linked from `results/README.md`.
- **Dry run by default.** Without an explicit apply flag, the command only reports, run by run, which files it would delete, how much space that frees, and which runs would lose files. Applying also requires a written reason.
- **Explicit selection.** The user names what to clean, for example by run ids or by age. Nothing is chosen implicitly.
- **Shared files are visible.** Because identical files are stored once, a file can belong to several runs. A file is deleted only when every run that references it is selected, and the dry run lists any file kept for that reason.
- **Recorded before deleting.** For each file, the command first appends a cleanup record (the file's hash and size, the affected runs, when, why, and who ran it), then deletes it. A crash midway still leaves every deletion explained.
- **Explained afterwards.** Verification and summaries report a deleted artifact as "deleted by cleanup on DATE: REASON". A missing artifact with no cleanup record is an integrity failure.
- The command never touches the ledger, logs, manifests, or cleanup records, and nothing outside the artifact store.

## Consequences

- **Benefit:** experiment outputs survive the run and are verifiable, storage can be reduced deliberately, and every missing file has a recorded explanation the user can read.
- **Tradeoff:** the store grows until someone cleans it, and storage use depends on what experiments write.
- **Follow-up:** artifact storage and the cleanup command are separate PRs, in that order. The cleanup PR adds the README section and a test that runs a dry run, applies it, then verifies that every missing file is explained. The size limit and its setting are chosen in the storage PR. The evidence archives of issue #6 live under `results/evidence/`, separate from this store.
