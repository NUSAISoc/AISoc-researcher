"""Research question from docs/03-research-question.md.

Reads the first quoted line under the heading "The one main research question".
The template placeholder means the question is not set yet (value None).
"""
from __future__ import annotations

import re
from pathlib import Path

from .common import SourceResult, guarded, is_template, read_text

REL_PATH = "docs/03-research-question.md"
HEADING = re.compile(r"^#{1,6}\s+the one main research question\s*$", re.IGNORECASE)


def _parse(path: Path):
    lines = read_text(path).splitlines()
    for i, line in enumerate(lines):
        if HEADING.match(line.strip()):
            for nxt in lines[i + 1:]:
                s = nxt.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    break
                if s.startswith(">"):
                    q = s.lstrip(">").strip()
                    if not q or is_template(q):
                        return None
                    return q.strip("`").strip()
                break
            return None
    return SourceResult(REL_PATH, False, reason=f"heading 'The one main research question' not found in {REL_PATH}")


def read(root: Path) -> SourceResult:
    return guarded(REL_PATH, _parse, root)
