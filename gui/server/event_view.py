"""Turns events and dashboard interactions from the central log into what the dashboard shows.

Pure functions: no file access, no writes. The dashboard does not decide whether
an event is true; it only decides how to present it. Presentation safeguards:
- an event that verifies or rejects a finding, or settles a decision, is only
  shown as such if its actor is a human; from anyone else it is ignored and
  reported as a warning, so an agent can never appear to have approved something;
- findings enter as "unverified" and decisions as pending, whoever proposed them.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

HUMAN_ONLY = {
    "finding.verified", "finding.rejected",
    "decision.approved", "decision.rejected", "decision.revision_requested", "decision.deferred",
}
FAILED_OUTCOMES = {"failure": "failed", "timeout": "failed", "inconclusive": "inconclusive"}


def parse_ts(value: str) -> Optional[dt.datetime]:
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def short_time(value: str, now: dt.datetime) -> str:
    ts = parse_ts(value)
    if not ts:
        return value or "unknown time"
    local = ts.astimezone()
    return local.strftime("%H:%M") if local.date() == now.astimezone().date() else local.strftime("%d %b")


def hours_since(value: str, now: dt.datetime) -> float:
    ts = parse_ts(value)
    return max(round((now - ts).total_seconds() / 3600, 1), 0) if ts else 0


def _s(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def _short(run_id: str) -> str:
    return run_id[-8:] if len(run_id) > 8 else run_id


def _strings(value) -> List[str]:
    return [str(x) for x in value] if isinstance(value, list) else []


def build(events: List[Dict[str, Any]], now: dt.datetime, ledger_ids: set,
          interactions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    warnings: List[str] = []
    findings: Dict[str, Dict[str, Any]] = {}
    decisions: Dict[str, Dict[str, Any]] = {}
    runs: Dict[str, Dict[str, Any]] = {}
    actions: List[Dict[str, Any]] = []

    for ev in events:
        etype, actor, subj, data, at = ev["type"], ev["actor"], ev["subject"], ev.get("data") or {}, ev["at"]
        sid, version = subj["id"], subj["version"]
        if etype in HUMAN_ONLY and actor["kind"] != "human":
            warnings.append(f"ignored {etype} for {sid} from {actor['kind']} {actor['id']}: only a human can decide")
            continue

        # ----- findings -----
        if etype == "finding.inferred":
            findings[sid] = {
                "id": sid, "version": version, "verification": "unverified",
                "claim": _s(data.get("claim"), "(no claim given)"),
                "effect": _s(data.get("effect"), "Inferred effect: not stated"),
                "uncertainty": _s(data.get("uncertainty"), "uncertainty not stated"),
                "synthetic": bool(data.get("synthetic")),
                "inferredBy": {"session": actor["id"], "agent": _s(data.get("harness"), "unknown harness"),
                               "model": _s(data.get("model"), "unknown model"), "at": short_time(at, now)},
                "ids": " · ".join(x for x in (_s(data.get("campaign")), actor["id"]) if x),
                "waitingHours": hours_since(at, now),
                "links": _strings(data.get("links")) or ["Evidence"],
                "_last": at,
            }
        elif etype.startswith("finding."):
            f = findings.get(sid)
            if not f:
                warnings.append(f"{etype} for unknown finding {sid} ignored")
                continue
            f["version"], f["_last"] = version, at
            if etype == "finding.evidence_changed":
                if f["verification"] == "verified":
                    f["verification"] = "recheck"
                    f["waitingHours"] = hours_since(at, now)
                f["recheckReason"] = "Evidence changed since verification: " + _s(data.get("reason"), "no reason given")
            elif etype in ("finding.verified", "finding.rejected"):
                f["verification"] = "verified" if etype == "finding.verified" else "rejected"
                f["reviewedBy"] = {"verb": "Verified" if etype == "finding.verified" else "Rejected",
                                   "name": actor["id"], "at": short_time(at, now), "rationale": _s(data.get("rationale"))}
                f.pop("recheckReason", None)

        # ----- decisions -----
        elif etype == "decision.proposed":
            blocks = _strings(data.get("blocks"))
            decisions[sid] = {
                "state": "pending", "version": version, "at": at, "actor": actor, "data": data, "blocks": blocks,
            }
        elif etype.startswith("decision."):
            d = decisions.get(sid)
            if not d:
                warnings.append(f"{etype} for unknown decision {sid} ignored")
                continue
            d["version"] = version
            d["state"] = {"decision.approved": "approved", "decision.rejected": "rejected",
                          "decision.revision_requested": "revision requested", "decision.deferred": "pending"}[etype]
            if etype == "decision.deferred":
                d["deferredBy"] = actor["id"]

        # ----- runs -----
        elif etype == "run.started":
            runs[sid] = {"state": "running", "version": version, "at": at, "actor": actor, "data": dict(data)}
        elif etype == "run.progressed":
            if sid in runs:
                runs[sid]["version"] = version
                runs[sid]["data"].update({k: data[k] for k in ("unitsRecorded", "unitsTotal") if k in data})
        elif etype == "run.finished":
            r = runs.setdefault(sid, {"at": at, "actor": actor, "data": {}})
            r.update(state="finished", version=version, outcome=_s(data.get("outcome")), finishedAt=at)

        if etype != "run.progressed":  # progress is shown on the run itself, not in the audit
            actions.append(_action(ev, now))

    for rec in interactions or []:
        actions.append(_interaction(rec, now))

    work = [_decision_item(sid, d, now) for sid, d in decisions.items() if d["state"] == "pending"]
    for sid, r in runs.items():
        if r.get("state") == "running":
            work.append(_run_item(sid, r, "running", now))
        elif r.get("outcome") in FAILED_OUTCOMES and sid not in ledger_ids:
            work.append(_run_item(sid, r, FAILED_OUTCOMES[r["outcome"]], now))

    work = [{k: v for k, v in w.items() if v is not None} for w in work]
    ordered = sorted(findings.values(), key=lambda f: f["_last"], reverse=True)
    for f in ordered:
        f.pop("_last", None)
    return {
        "findings": ordered,
        "work": work,
        "actions": actions,
        "running": sum(1 for r in runs.values() if r.get("state") == "running"),
        "inconclusive": sum(1 for r in runs.values() if r.get("outcome") == "inconclusive"),
        "warnings": warnings,
    }


def _decision_item(sid: str, d: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    data, actor = d["data"], d["actor"]
    waiting = hours_since(d["at"], now)
    summary = f"Waiting {waiting:g} h" + (f" · blocks {len(d['blocks'])}" if d["blocks"] else "")
    if d.get("deferredBy"):
        summary += f" · deferred by {d['deferredBy']}"
    details = [["What changes", _s(data.get("summary"), "not stated")], ["Rationale", _s(data.get("rationale"), "not stated")]]
    if d["blocks"]:
        details.append(["Blocks", ", ".join(d["blocks"])])
    return {
        "id": sid, "version": d["version"], "resource": f"decisions/{sid}", "status": "decision",
        "type": _s(data.get("kind")) or None, "title": _s(data.get("title"), f"Decision {sid}"),
        "ids": " · ".join(x for x in (_s(data.get("campaign")), actor["id"]) if x), "summary": summary,
        "urgency": {"paused": bool(data.get("pausesAgent")), "blocks": len(d["blocks"]), "waitingHours": waiting},
        "experiment": [x for x in (_s(data.get("campaign")), _s(data.get("hypothesis"))) if x] or ["not stated"],
        "agent": ["proposed by " + actor["id"], _s(data.get("harness"), "unknown harness"), _s(data.get("model"), "unknown model")],
        "details": details, "actions": ["review"], "links": _strings(data.get("links")),
    }


def _run_item(sid: str, r: Dict[str, Any], status: str, now: dt.datetime) -> Dict[str, Any]:
    data, actor = r["data"], r["actor"]
    rec, total = data.get("unitsRecorded"), data.get("unitsTotal")
    if status == "running":
        title = f"Run {_short(sid)} running"
        if isinstance(rec, int) and isinstance(total, int):
            summary = f"{rec} of {total} units recorded"
        elif isinstance(rec, int):
            summary = f"{rec} units recorded (total not known)"
        else:
            summary = f"started {short_time(r['at'], now)}"
    else:
        title = f"Run {_short(sid)} " + ("inconclusive" if status == "inconclusive" else r.get("outcome", "failed"))
        summary = f"finished {short_time(r.get('finishedAt', r['at']), now)}"
    return {
        "id": sid, "version": r.get("version", 1), "resource": f"runs/{sid}", "status": status, "type": None,
        "title": title, "ids": _s(data.get("experiment"), "unnamed experiment"), "summary": summary,
        "urgency": {"paused": False, "blocks": 0, "waitingHours": 0},
        "experiment": [x for x in (_s(data.get("experiment")), _s(data.get("mode")), _s(data.get("campaign"))) if x] or ["not stated"],
        "agent": [actor["id"], _s(data.get("harness"), "unknown harness"), _s(data.get("model"), "unknown model")],
        "details": [["Run ID", sid], ["Started (UTC)", r["at"]], ["Outcome", r.get("outcome", "still running")]],
        "actions": [], "links": [], "synthetic": _s(data.get("mode")) == "synthetic",
    }


WHAT = {
    "run.started": "Started run {s}",
    "run.progressed": "Run {s} progressed",
    "run.finished": "Run {s} finished: {outcome}",
    "finding.inferred": "Inferred finding {s}",
    "finding.evidence_changed": "Evidence changed for finding {s}",
    "finding.verified": "Verified finding {s}",
    "finding.rejected": "Rejected finding {s}",
    "decision.proposed": "Proposed decision {s}",
    "decision.approved": "Approved decision {s}",
    "decision.rejected": "Rejected decision {s}",
    "decision.revision_requested": "Requested revision of decision {s}",
    "decision.deferred": "Deferred decision {s}",
    "agent.paused": "Agent {s} paused",
    "agent.resumed": "Agent {s} resumed",
}


def _action(ev: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    data = ev.get("data") or {}
    what = WHAT.get(ev["type"], ev["type"] + " {s}").format(s=ev["subject"]["id"], outcome=_s(data.get("outcome"), "?"))
    context = _s(data.get("title") or data.get("claim") or data.get("reason") or data.get("experiment"))
    out = {"at": short_time(ev["at"], now), "_ts": ev["at"], "actor": {"kind": ev["actor"]["kind"], "name": ev["actor"]["id"]}, "what": what}
    if context:
        out["context"] = context
    if ev["actor"]["kind"] == "human" and data.get("rationale"):
        out["rationale"] = _s(data.get("rationale"))
    return out


def _interaction(rec: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    """A command sent from the dashboard, shown with the reply it got."""
    e = rec.get("entry") or {}
    outcome = e.get("outcome") or {}
    command = _s(e.get("command"), "unknown command")
    target, _, action = command.rpartition(":")
    what = f"Requested {action or 'command'} of {target.split('/')[-1] or '?'}"
    reply = "not available yet (#6)" if outcome.get("status") == "UNSUPPORTED" else _s(outcome.get("message") or outcome.get("status"), "no reply")
    out = {"at": short_time(rec.get("loggedAt", ""), now), "_ts": rec.get("loggedAt", ""),
           "actor": {"kind": "human", "name": _s(e.get("actor"), "researcher")}, "what": what, "context": reply}
    if e.get("rationale"):
        out["rationale"] = _s(e.get("rationale"))
    return out
