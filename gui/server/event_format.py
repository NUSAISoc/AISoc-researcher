"""The event format the dashboard accepts (gui/contract/event-log.schema.json).

This is the dashboard's input hook: any producer that sends events in this
shape is displayed. The dashboard does not decide whether an event is true;
it only checks that it is well formed.
"""
from __future__ import annotations

import re
from typing import Any, Tuple

KINDS = ("human", "agent", "system")
ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def check(ev: Any) -> Tuple[bool, str]:
    """Return (True, "") for a well-formed event, else (False, reason)."""
    if not isinstance(ev, dict):
        return False, "not a JSON object"
    if ev.get("v") != 1:
        return False, "unsupported envelope version (expected v: 1)"
    if not isinstance(ev.get("id"), str) or not ID.match(ev["id"]):
        return False, "missing or invalid id"
    if not isinstance(ev.get("type"), str) or not ev["type"]:
        return False, "missing type"
    if not isinstance(ev.get("at"), str) or not TIME.match(ev["at"]):
        return False, "at must be UTC, YYYY-MM-DDTHH:MM:SSZ"
    a = ev.get("actor")
    if not isinstance(a, dict) or a.get("kind") not in KINDS or not isinstance(a.get("id"), str) or not a["id"]:
        return False, "actor must be {kind: human|agent|system, id}"
    s = ev.get("subject")
    if (not isinstance(s, dict) or not isinstance(s.get("type"), str) or not isinstance(s.get("id"), str)
            or not ID.match(s["id"]) or not isinstance(s.get("version"), int) or isinstance(s.get("version"), bool)
            or s["version"] < 1):
        return False, "subject must be {type, id, version >= 1}"
    if not isinstance(ev.get("data", {}), dict):
        return False, "data must be an object"
    return True, ""
