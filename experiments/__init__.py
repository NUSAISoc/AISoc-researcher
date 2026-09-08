"""Sandboxed autoresearch experiment harness.

The runner executes an experiment automatically inside a disposable workspace
the repository creates, writes a deterministic per-run log to ``results/logs/``,
and appends one audit row to ``results/ledger.csv``. Synthetic mode is the
default and is deterministic and offline. A live run is fail-closed on missing
authorization or credentials and never silently falls back to synthetic. The
runner never writes outside ``experiments/`` and ``results/`` and never
fabricates data into the results templates or ``docs/06-experimental-results.md``.
"""
