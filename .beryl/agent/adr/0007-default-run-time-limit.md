# ADR 0007: Default Run Time Limit

## Status

Accepted on 2026-10-05 in the issue #9 design review (decision D4).

## Context

Nothing limits how long a run takes, although the documentation says timeouts are recorded. A hung run never finishes and is never recorded.

## Decision

- Every run has a time limit, set with `EXPERIMENT_TIMEOUT_SECONDS`. The default is 3600 (1 hour).
- Running without a limit requires an explicit `0`. A negative or non-integer value is a refused attempt ([ADR 0004](0004-record-every-refused-run.md)).
- When the limit is reached, the backend stops the run ([ADR 0008](0008-runner-and-execution-backend.md)) and the runner records status `timeout`. The log states the limit and the elapsed time, and files written so far are kept ([ADR 0006](0006-artifact-store-and-cleanup.md)).
- The limit is part of the run's recorded configuration. On Slurm it becomes the job's walltime, and a Slurm `TIMEOUT` is recorded as `timeout`.

## Consequences

- **Benefit:** a hung run ends and is recorded instead of running forever.
- **Tradeoff:** a long experiment must raise the limit or set `0`; forgetting to do so ends the run at one hour.
- **Follow-up:** implemented with the killed-run records ([ADR 0009](0009-started-markers-and-lost-runs.md)) on top of the child-process backend. `experiments/README.md` gains the new variable in its configuration table.
