# ADR 0008: Runner and Execution Backend Boundary

## Status

Accepted on 2026-10-05 in the issue #9 design review (decision D5).

## Context

Issue #9 adds execution backends: this machine now, a Slurm cluster later. Local and Slurm runs must share one provenance and result contract. A time limit can only be enforced safely by stopping a separate process: a thread cannot be killed, and `signal.alarm` does not exist on Windows.

## Decision

- **The runner** validates the request, assigns the run id, and writes all evidence: the started marker, ledger row, log, artifact manifest, and final status.
- **A backend** only runs the experiment and reports how it ended: finished, failed with an error, timed out, or cancelled. It writes no evidence.
- **A backend that cannot tell how a run ended** (for example, when the cluster is unreachable) reports `unknown`. The runner then records no final status and leaves the run open ([ADR 0009](0009-started-markers-and-lost-runs.md)). Lost contact is never treated as completion.
- **The local backend** runs the experiment in a separate child process, inside the sandbox, so it can stop the run at the time limit. Ctrl-C in the parent stops the child and is recorded as `cancelled`, keeping today's behaviour from #12.
- **Slurm** becomes a second backend with the same contract.

## Consequences

- **Benefit:** one evidence contract for every backend, and a time limit that works on Windows, macOS, Linux, and clusters.
- **Tradeoff:** an experiment's records cross a process boundary, so they must be serializable. Starting a child process adds a little overhead to each run.
- **Follow-up:** some existing tests replace `get_experiment` inside the test process, and a child process does not see that replacement. Those tests switch to small real test experiments (crash, interrupt, sleep) with the same assertions. Changing test files requires updating `tests/.manifest.sha256`, which must not be regenerated on Windows (#14). `.beryl/agent/architecture.md` describes the boundary once the local backend lands.
