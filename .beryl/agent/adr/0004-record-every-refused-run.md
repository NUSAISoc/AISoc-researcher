# ADR 0004: Record Every Refused Run

## Status

Accepted on 2026-10-05 in the issue #9 design review (decision D1).

## Context

Some run attempts are refused before the experiment starts: an unknown experiment name, an invalid setting, or live mode without authorization or credentials. Today a configuration error exits with code 2 and writes nothing, and an unknown experiment name raises out of `run()` before any record exists. The Autoresearch Sandbox Gate says refusals are results, and issue #9 requires that runs cannot disappear from campaign summaries.

## Decision

- Every attempt to run the runner writes exactly one ledger row and one log, including attempts refused before the experiment starts. Listing experiments (`--list`) and `--help` are not run attempts.
- A refused attempt has status `refused` and a short reason, such as `unknown experiment` or `live authorization missing`. The reason goes in a new ledger column, `reason`, and in the run's one log record. It names settings and variables, never their values, so it can never contain a secret.
- Fields that cannot be known yet, such as `config_hash` when the configuration did not parse, are left blank, never guessed. The requested experiment name is recorded as given, because it is a fact about the attempt.
- No sandbox is created for a refused attempt. The process exit code stays non-zero, as today.

## Consequences

- **Benefit:** every attempt is visible, which makes failures easier to debug and gives an audit trail of live runs attempted without authorization.
- **Tradeoff:** the ledger gains rows that are not experiment results; summaries must show them separately from runs that executed.
- **Follow-up:** the implementing PR adds the `reason` column, updates `experiments/README.md` and the ledger schema in `results/README.md`, and adds one test per refusal path (unknown name, invalid setting, live without authorization, and the mode check from #13 once it lands). Rows written before the change keep their shape.
