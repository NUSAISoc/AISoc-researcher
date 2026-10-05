# ADR 0009: Started Markers and Lost Runs

## Status

Accepted on 2026-10-05 in the issue #9 design review (decision D6).

## Context

A process killed outright (SIGKILL, a crashed machine, a dead cluster node) runs no handler, so it cannot record itself. Issue #9 requires that every submitted run leaves evidence, including runs that never finish.

## Decision

- Before the backend starts a run, the runner writes a small started marker: the run id, start time, backend, and what identifies the process, such as host and process id locally or job id on Slurm.
- A run is open while it has a marker but no final ledger row.
- An open run is recorded as `lost` only when its process is known to be gone: on the same host, the process no longer exists; on Slurm, the scheduler reports the job ended. The `lost` row states what is known (the run never finished) and leaves unknown fields blank. It does not invent a result.
- If ownership cannot be established (another host, or the cluster is unreachable), the run stays open and is reported as unresolved, never as lost. This matches the rule issue #6 (PR #18) uses for abandoned locks: act only once the owner process is known to be dead.
- What happens to files left in a lost run's sandbox is decided in the implementing PR; they are never silently deleted.

## Consequences

- **Benefit:** a run that dies without warning still appears in the ledger and in summaries.
- **Tradeoff:** detection happens later, when the check runs, not at the moment of death. A run on an unreachable machine can stay unresolved indefinitely, and is shown as such.
- **Follow-up:** implemented in the same PR as the time limit ([ADR 0007](0007-default-run-time-limit.md)). Process identity must survive process-id reuse, for example by also checking the process start time. Markers are kept, not deleted, so a run's history stays complete.
