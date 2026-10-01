"""Dependency-free command line for research workflow records."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .records import WorkflowError, MANIFEST, build_manifest, canonical_json, check_manifest, write_manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Validate canonical records and generated index")
    sub.add_parser("manifest", help="Print the deterministic index without writing")
    sub.add_parser("rebuild", help="Regenerate the index from canonical records")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            check_manifest(args.root)
            print("workflow: records and manifest OK")
        elif args.command == "manifest":
            print(canonical_json(build_manifest(args.root)), end="")
        else:
            write_manifest(args.root)
            print(f"workflow: regenerated {MANIFEST}")
        return 0
    except (WorkflowError, OSError, UnicodeError) as exc:
        print(f"workflow: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
