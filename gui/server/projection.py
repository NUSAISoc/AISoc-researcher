"""Builds the read model the dashboard displays, from the source readers.

Rules:
- Read only. Nothing here writes to the repository.
- Each section is built separately, so a failure in one source only affects
  the parts of the page that depend on it (shown as "unavailable").
- Anything without a source is NOT_TRACKED, never zero.
- No research meaning is invented: run status comes straight from the ledger
  ("ok" -> ok, "error" -> failed). Other ledger statuses are not guessed; they
  are skipped and reported as warnings.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import List, Optional

from . import event_view
from .sources import event_log, ledger, reading_list, references, research_question, results_templates
from .sources.common import NOT_TRACKED, SourceResult, unavailable

SCHEMA_VERSION = 1
STATUS_MAP = {"ok": "ok", "error": "failed"}
RECENT_OK = 3
RECENT_ACTIONS = 8


def _parse_ts(value: str) -> Optional[dt.datetime]:
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def _short_time(value: str, now: dt.datetime) -> str:
    ts = _parse_ts(value)
    if not ts:
        return value or "unknown time"
    local = ts.astimezone()
    if local.date() == now.astimezone().date():
        return local.strftime("%H:%M")
    return local.strftime("%d %b")


def _short_id(run_id: str) -> str:
    return run_id[-8:] if len(run_id) > 8 else run_id


def _run_item(row: dict, status: str, root: Path, rows: List[dict], now: dt.datetime) -> dict:
    run_id = row["run_id"]
    ts = _parse_ts(row.get("timestamp_utc", ""))
    waiting = round((now - ts).total_seconds() / 3600, 1) if (ts and status == "failed") else 0
    mode = row.get("mode") or "unknown mode"
    experiment = row.get("experiment") or "unnamed experiment"
    links = []
    if ledger.log_path(root, run_id, rows):
        links.append({"label": "Log", "href": f"/api/runs/{run_id}/log"})
    return {
        "id": run_id,
        "version": 1,
        "resource": f"runs/{run_id}",
        "status": status,
        "title": f"Run {_short_id(run_id)} " + ("errored" if status == "failed" else "completed"),
        "ids": experiment,
        "summary": f"{_short_time(row.get('timestamp_utc', ''), now)} · {row.get('num_records') or '?'} records · {mode}",
        "urgency": {"paused": False, "blocks": 0, "waitingHours": max(waiting, 0)},
        "experiment": [experiment, mode, "config " + (row.get("config_hash") or "unknown")],
        "agent": ["not recorded"],
        "details": [
            ["Run ID", run_id],
            ["Recorded at (UTC)", row.get("timestamp_utc") or "unknown"],
            ["Mode", mode],
            ["Records", row.get("num_records") or "unknown"],
            ["Config hash", row.get("config_hash") or "unknown"],
            ["Notes", row.get("notes") or "none"],
        ],
        "actions": [],  # no command can be carried out until the control plane (#6) exists
        "links": links,
        "synthetic": (row.get("synthetic") or "").lower() == "true",
    }


def build_project(root: Path, now: dt.datetime) -> dict:
    rq = research_question.read(root)
    data = results_templates.read(root)
    return {
        "researchQuestion": rq.value if rq.ok else unavailable(rq.reason),
        "stage": NOT_TRACKED,
        "modelTraffic": NOT_TRACKED,
        "data": data.value if data.ok else unavailable(data.reason),
        "asOf": now.astimezone().strftime("%H:%M"),
    }


def build_runs(root: Path) -> SourceResult:
    return ledger.read(root)


def build_events(root: Path, runs: SourceResult, now: dt.datetime):
    """Read the central log and turn it into dashboard parts.

    Returns (SourceResult, view or None, has_events). The view also carries the
    dashboard's own interactions; findings and decisions count as tracked only
    once at least one event has been received from a source.
    """
    log = event_log.read(root)
    if not log.ok:
        return log, None, False
    ledger_ids = {r["run_id"] for r in runs.value} if runs.ok else set()
    events, interactions = log.value["events"], log.value["interactions"]
    if not events and not interactions:
        return log, None, False
    return log, event_view.build(events, now, ledger_ids, interactions), bool(events)


def build_pipeline(root: Path, runs: SourceResult, events=None) -> list:
    refs = references.read(root)
    unread = reading_list.read(root)
    if refs.ok or unread.ok:
        evidence = {"stage": "Evidence", "icon": "book", "counts": [
            ["read", refs.value["total"] if refs.ok else NOT_TRACKED],
            ["unread", unread.value if unread.ok else NOT_TRACKED],
            ["contradicted", NOT_TRACKED],
        ]}
    else:
        evidence = {"stage": "Evidence", "icon": "book", "tracked": True, "available": False, "reason": refs.reason}
    if runs.ok:
        rows = runs.value
        run_stage = {"stage": "Runs", "icon": "play", "counts": [
            ["ok", sum(1 for r in rows if r.get("status") == "ok")],
            ["failed", sum(1 for r in rows if r.get("status") == "error"), "bad"],
            ["inconclusive", events["inconclusive"] if events else NOT_TRACKED],
            ["running", events["running"] if events else NOT_TRACKED],
        ]}
    else:
        run_stage = {"stage": "Runs", "icon": "play", "tracked": True, "available": False, "reason": runs.reason}
    return [
        evidence,
        {"stage": "Opportunities", "icon": "bulb", "tracked": False},
        {"stage": "Campaigns", "icon": "flask", "tracked": False},
        run_stage,
        _findings_stage(events),
    ]


def _findings_stage(events) -> dict:
    if not events:
        return {"stage": "Findings", "icon": "chart", "tracked": False}
    fs = events["findings"]
    return {"stage": "Findings", "icon": "chart", "counts": [
        ["verified", sum(1 for f in fs if f["verification"] == "verified")],
        ["to review", sum(1 for f in fs if f["verification"] in ("unverified", "recheck"))],
        ["rejected", sum(1 for f in fs if f["verification"] == "rejected")],
    ]}


def build_work(root: Path, runs: SourceResult, now: dt.datetime) -> List[dict]:
    if not runs.ok:
        return []
    rows = runs.value
    items = []
    for row in rows:
        if row.get("status") == "error":
            items.append(_run_item(row, "failed", root, rows, now))
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    for row in ok_rows[-RECENT_OK:][::-1]:
        items.append(_run_item(row, "ok", root, rows, now))
    return items


def build_actions(runs: SourceResult, now: dt.datetime, events=None):
    """Recent actions from the ledger and the event log, newest first."""
    if not runs.ok and not events:
        return unavailable(runs.reason)
    out = []
    if runs.ok:
        for row in runs.value:
            out.append({
                "_ts": row.get("timestamp_utc", ""),
                "at": _short_time(row.get("timestamp_utc", ""), now),
                "actor": {"kind": "unknown", "name": "unknown actor"},
                "what": f"Run {_short_id(row['run_id'])} recorded: {row.get('status') or 'no status'}",
                "context": f"{row.get('experiment') or 'unnamed'}, {row.get('mode') or 'unknown mode'}",
            })
    if events:
        out.extend(events["actions"])
    out.sort(key=lambda a: a.get("_ts", ""), reverse=True)
    return [{k: v for k, v in a.items() if k != "_ts"} for a in out[:RECENT_ACTIONS]]


def build_overview(root: Path, now: Optional[dt.datetime] = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    runs = build_runs(root)
    warnings = list(runs.warnings)
    if runs.ok:
        unknown = sorted({r.get("status") for r in runs.value if r.get("status") not in STATUS_MAP})
        if unknown:
            warnings.append("ledger statuses not shown: " + ", ".join(s or "(empty)" for s in unknown))

    log, view, has_events = build_events(root, runs, now)
    warnings.extend(log.warnings)
    if view:
        warnings.extend(view["warnings"])
    if not log.ok:
        events_marker = unavailable(log.reason)
    elif not has_events:
        events_marker = NOT_TRACKED
    else:
        events_marker = None
    events = view if has_events else None  # interactions alone do not make findings "tracked"

    def safe(name, fn, fallback):
        # A bug in one section must not take down the whole overview.
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{name} could not be built ({type(exc).__name__})")
            return fallback

    return {
        "schemaVersion": SCHEMA_VERSION,
        "project": safe("project", lambda: build_project(root, now), {
            "researchQuestion": unavailable("project section failed"), "stage": NOT_TRACKED,
            "modelTraffic": NOT_TRACKED, "data": unavailable("project section failed"),
            "asOf": now.astimezone().strftime("%H:%M")}),
        "pipeline": safe("pipeline", lambda: build_pipeline(root, runs, events), []),
        "work": safe("work", lambda: build_work(root, runs, now) + (view["work"] if view else []), []),
        # Findings and decisions come from the event log; without it they are not tracked.
        "findings": events_marker or events["findings"],
        "decisions": events_marker or {"tracked": True},
        "actions": safe("actions", lambda: build_actions(runs, now, view), unavailable("actions section failed")),
        "warnings": warnings,
    }
