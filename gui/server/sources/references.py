"""Evidence read so far, from references.md.

Counts numbered entries under "All Readings Read So Far" by reading-depth tag.
Template entries such as `<Author, B. (Year)...>` are ignored.
"""
from __future__ import annotations

import re
from pathlib import Path

from .common import guarded, is_template, read_text

REL_PATH = "references.md"
SECTION = re.compile(r"^##\s+all readings read so far\s*$", re.IGNORECASE)
ENTRY = re.compile(r"^\s*\d+\.\s+(.*)$")
TAG = re.compile(r"\[(full|abstract|artifact|non-peer-reviewed)\]", re.IGNORECASE)


def _parse(path: Path):
    by_depth = {"full": 0, "abstract": 0, "artifact": 0, "non-peer-reviewed": 0, "untagged": 0}
    inside = False
    for line in read_text(path).splitlines():
        if line.startswith("## "):
            inside = bool(SECTION.match(line.strip()))
            continue
        if not inside:
            continue
        m = ENTRY.match(line)
        if not m or is_template(m.group(1)):
            continue
        tag = TAG.search(m.group(1))
        by_depth[tag.group(1).lower() if tag else "untagged"] += 1
    return {"total": sum(by_depth.values()), "byDepth": by_depth}


def read(root: Path):
    return guarded(REL_PATH, _parse, root)
