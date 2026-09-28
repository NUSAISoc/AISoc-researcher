"""Unread candidates, from readingList.md (table rows, excluding header and template rows)."""
from __future__ import annotations

import re
from pathlib import Path

from .common import guarded, is_template, read_text

REL_PATH = "readingList.md"
SEPARATOR = re.compile(r"^\|\s*:?-{3,}")


def _parse(path: Path):
    count, seen_sep = 0, False
    for line in read_text(path).splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if seen_sep and s:
                seen_sep = False  # table ended
            continue
        if SEPARATOR.match(s):
            seen_sep = True
            continue
        if not seen_sep:
            continue  # header row
        first = s.strip("|").split("|")[0]
        if is_template(first) or not first.strip():
            continue
        count += 1
    return count


def read(root: Path):
    return guarded(REL_PATH, _parse, root)
