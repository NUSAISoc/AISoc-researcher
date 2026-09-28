"""Server configuration. The bind address is fixed to loopback on purpose."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"


@dataclass(frozen=True)
class Config:
    root: Path = REPO_ROOT
    web_root: Path = WEB_ROOT
    port: int = DEFAULT_PORT
    actor: str = "researcher-1"
    poll_seconds: float = 2.0
    # External event files the dashboard imports into its central log (read only).
    event_files: tuple = ("control/events.jsonl",)


def from_args(argv=None) -> Config:
    p = argparse.ArgumentParser(prog="python3 -m gui.server", description="AISoc Researcher dashboard server (read-only, localhost only)")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root to read (default: this repository)")
    p.add_argument("--actor", default="researcher-1", help="actor recorded on commands")
    p.add_argument("--events", action="append", metavar="PATH",
                   help="repository-relative event file to import (repeatable; default control/events.jsonl)")
    a = p.parse_args(argv)
    return Config(root=a.root.resolve(), port=a.port, actor=a.actor,
                  event_files=tuple(a.events) if a.events else ("control/events.jsonl",))
