"""Disposable sandbox workspace for a single experiment run.

Each run gets its own directory under ``experiments/workspaces/<run_id>/``. The
sandbox guarantees that any path the experiment asks to write resolves to a
location inside that directory: a traversal outside the sandbox raises
``SandboxViolation`` rather than escaping. This is the containment boundary that
lets experiments run automatically without touching researcher-owned files.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .config import WORKSPACES_DIR


class SandboxViolation(RuntimeError):
    """Raised when an experiment tries to write outside its sandbox."""


class Sandbox:
    def __init__(self, run_id: str, root: Path | None = None) -> None:
        base = WORKSPACES_DIR if root is None else root
        self.run_id = run_id
        self.path = (base / run_id).resolve()

    def create(self) -> "Sandbox":
        self.path.mkdir(parents=True, exist_ok=True)
        return self

    def resolve(self, relative: str) -> Path:
        """Resolve a relative path inside the sandbox, refusing any escape."""
        candidate = (self.path / relative).resolve()
        try:
            candidate.relative_to(self.path)
        except ValueError as exc:
            raise SandboxViolation(
                f"path {relative!r} escapes the sandbox {self.path}"
            ) from exc
        return candidate

    def write_text(self, relative: str, text: str) -> Path:
        target = self.resolve(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def cleanup(self) -> None:
        """Remove the sandbox. Runs are disposable by design."""
        if self.path.exists():
            shutil.rmtree(self.path)

    def __enter__(self) -> "Sandbox":
        return self.create()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()
