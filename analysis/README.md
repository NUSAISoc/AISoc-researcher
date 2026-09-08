# Analysis

Scripts that turn the structured logs the runner wrote under `results/` into summary statistics and figures. They read only recorded data and never fabricate values.

## Summarise a run

```bash
python3 -m analysis.summarize results/logs/<run_id>.jsonl
```

This reports record counts by condition and status and the mean of a numeric field when present. It prints "nothing to summarise" when the log is empty.

## Making it your analysis

Replace `summarize.py` with the pre-registered analysis from `docs/07-statistical-analysis.md`. Read from `results/`, write figures into `report/figures/`, and mirror the findings into `docs/06-experimental-results.md` and the report per the synchronization contract. Only run this on real data; the synthetic runner's output is for exercising the pipeline, not for reporting results.
