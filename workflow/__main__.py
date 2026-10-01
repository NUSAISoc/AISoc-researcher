"""Dependency-free command line for research workflow records."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .records import WorkflowError, MANIFEST, build_manifest, canonical_json, check_manifest, write_manifest, load_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Validate canonical records and generated index")
    check.add_argument("--base", help="Also validate record transitions and history against a Git base")
    sub.add_parser("manifest", help="Print the deterministic index without writing")
    sub.add_parser("rebuild", help="Regenerate the index from canonical records")
    propose = sub.add_parser("propose", help="Prepare a diff without changing approved files")
    propose.add_argument("--changes", required=True, type=Path, help="JSON mapping repository paths to replacement text")
    reversal = sub.add_parser("rollback", help="Prepare a reviewed reversal of an applied proposal")
    reversal.add_argument("--digest", required=True)
    for command in (propose, reversal):
        command.add_argument("--author", required=True)
        command.add_argument("--reason", required=True)
        command.add_argument("--save", action="store_true", help="Save the proposal at its digest-named review path")
        command.add_argument("--trusted-base", default="origin/main")
    validate = sub.add_parser("validate", help="Check proposal integrity, inputs, and transitions offline")
    apply = sub.add_parser("apply", help="Verify human GitHub review and apply the exact proposal")
    for command in (validate, apply):
        command.add_argument("--proposal", required=True, type=Path)
    apply.add_argument("--pull-number", required=True, type=int)
    apply.add_argument("--trusted-base", default="origin/main")
    sub.add_parser("recover", help="Recover an interrupted transaction without overwriting concurrent edits")
    run_ref = sub.add_parser("run-reference", help="Print exact references to an existing runner ledger/log")
    run_ref.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            check_manifest(args.root)
            if args.base:
                from .changes import validate_tree_change
                validate_tree_change(args.root, args.base)
            print("workflow: records and manifest OK")
        elif args.command == "manifest":
            print(canonical_json(build_manifest(args.root)), end="")
        elif args.command == "rebuild":
            write_manifest(args.root)
            print(f"workflow: regenerated {MANIFEST}")
        elif args.command in {"propose", "rollback"}:
            from .changes import propose_change, propose_rollback
            from .records import safe_path
            if args.command == "propose":
                proposal = propose_change(args.root, load_json(args.changes.read_text(encoding="utf-8")),
                    author=args.author, reason=args.reason, trusted_ref=args.trusted_base)
            else:
                proposal = propose_rollback(args.root, args.digest, author=args.author, reason=args.reason, trusted_ref=args.trusted_base)
            if args.save:
                path = safe_path(args.root, f"docs/workflow/proposals/{proposal['digest']}.json")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(canonical_json(proposal), encoding="utf-8")
                print(f"workflow: proposal pending review at {path.relative_to(args.root.resolve())}")
                print(proposal["diff"], end="")
            else:
                print(canonical_json(proposal), end="")
        elif args.command in {"validate", "apply"}:
            from .changes import validate_proposal, apply_approved_change
            proposal = load_json(args.proposal.read_text(encoding="utf-8"))
            if args.command == "validate":
                validate_proposal(args.root, proposal)
                print("workflow: proposal valid; approval still required")
            else:
                apply_approved_change(args.root, proposal, pull_number=args.pull_number, trusted_ref=args.trusted_base)
                print("workflow: reviewed change applied; history preserved and manifest regenerated")
        elif args.command == "run-reference":
            from .records import run_reference
            print(canonical_json(run_reference(args.root, args.run_id)), end="")
        else:
            from .transaction import recover
            recover(args.root)
            print("workflow: transaction recovered")
        return 0
    except (WorkflowError, OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"workflow: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
