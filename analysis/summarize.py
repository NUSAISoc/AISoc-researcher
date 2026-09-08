"""Summarise a run log into simple, honest statistics.

This reads one ``results/logs/<run_id>.jsonl`` file and reports counts by
condition and status, plus the mean of a chosen numeric field when present. It
computes nothing when the log is empty and never invents values. Replace or
extend it with the pre-registered analysis from ``docs/07-statistical-analysis.md``
once real data exists.

Usage:

    python3 -m analysis.summarize results/logs/<run_id>.jsonl [--value-field synthetic_value]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Mapping


def load_records(log_path: Path) -> List[Mapping[str, object]]:
    records: List[Mapping[str, object]] = []
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def summarize(records: List[Mapping[str, object]], value_field: str = "synthetic_value") -> Dict[str, object]:
    summary: Dict[str, object] = {
        "num_records": len(records),
        "by_condition": dict(Counter(str(r.get("condition", "unknown")) for r in records)),
        "by_status": dict(Counter(str(r.get("status", "unknown")) for r in records)),
    }
    values = [r[value_field] for r in records if isinstance(r.get(value_field), (int, float))]
    summary["value_field"] = value_field
    summary["value_count"] = len(values)
    summary["value_mean"] = (sum(values) / len(values)) if values else None
    return summary


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarise an experiment run log")
    parser.add_argument("log_path", type=Path, help="path to a results/logs/<run_id>.jsonl file")
    parser.add_argument("--value-field", default="synthetic_value")
    args = parser.parse_args(argv)

    if not args.log_path.is_file():
        print(f"log not found: {args.log_path}")
        return 1

    records = load_records(args.log_path)
    if not records:
        print("no records in log; nothing to summarise")
        return 0

    summary = summarize(records, value_field=args.value_field)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
