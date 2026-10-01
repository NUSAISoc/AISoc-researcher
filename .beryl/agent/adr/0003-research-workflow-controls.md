# ADR 0003: Research Workflow Records and Reviewed Changes

## Status

Accepted by the researcher on 2026-10-01 following the issue #6 design and implementation-plan discussion.

## Context

The Git-based harness has canonical study files, dated decisions, a runner-owned ledger, and documented review policy, but no shared lifecycle index or revision-bound edit contract. Agents must not silently change research meaning, safety rules, or history. Event sourcing and linked versioned documents were compared with a simpler files-plus-manifest approach.

## Decision

Use readable Markdown lifecycle records with a fenced JSON metadata block, exact revision links, and a deterministic generated manifest. Keep prior record revisions and dated application receipts as audited history. Use a standard-library Python package under `workflow/` for validation, proposals, verified application, and recoverable transactions. Existing study files and runner artifacts retain their authority.

Bind approval to a reviewed proposal digest and GitHub commit, verify human reviews through a read-only adapter, and obtain reviewer policy from a trusted Git base. Do not treat an editable approval field as authority. Offline proposals remain pending when review verification is unavailable. Protected branches, reviewer-role assignments, and backups are external ownership and must be configured by maintainers.

## Consequences

- Benefit: readable, offline-capable records fit the existing harness and expose shared state without a new database.
- Tradeoff: generated-index parity, semantic conflicts, retention, and interrupted edits require explicit checks. A CLI cannot prevent privileged direct filesystem edits.
- Rejected alternatives: full event sourcing adds replay/projection responsibilities; unstructured links alone cannot support uniform checks; a separately edited manifest would create another authority.
- Follow-up: implement and verify the [workflow contract](../../../docs/00-research-workflow-controls.md), keep test fixtures separate from study evidence, and revisit event storage if concurrency or replay becomes central.

## Clarification after PR #18 review

Terminal run records require reviewed immutable archives of the existing runner ledger row and exact log bytes under `results/evidence/`. Runtime logs are ignored and the committed ledger can be header-only, so depending only on those local paths would break CI and remote approval verification. Prepare the archive without writing, include its text with the terminal record proposal, and retain it through reviewed application. Reject changes to retained archives and mismatches with available runtime originals. The runner keeps source authority. Skipping absent evidence was rejected because a fresh checkout must still verify the terminal record. This repair does not change experiment behavior or fabricate/promote study data.

Git-base validation accepts multiple reviewed steps on one branch by checking the entire retained revision chain and a receipt for each step. It applies the same per-step lifecycle and immutability rules as local application, including the referenced restoration for rollback. It remains structural validation and does not supply external human authorization.

Recovery also inspects abandoned locks when no journal exists, because remote approval verification takes place before the write journal is created. Remove locks only after establishing their owner process is dead; preserve live or uncertain-owner locks. Journal recovery continues to protect subsequent concurrent edits.
