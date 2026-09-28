"""HTTP layer: routing, safety checks, static files, commands and the event stream.

Safety rules enforced here:
- The server only listens on 127.0.0.1 (see config.HOST).
- Requests must be addressed to 127.0.0.1 or localhost (blocks DNS rebinding).
- POST requests from another web origin are refused (blocks cross-site requests).
- Static files are served only from gui/web, never from elsewhere.
- Run logs are served only for run IDs present in the ledger.
- Research files are only read. The one thing the server writes is its own
  central log (gui/.local/log.jsonl, not tracked by git): events received from
  sources, and every command sent from the dashboard with its reply. Commands
  are validated and then refused with 501 until the control plane (#6) can
  carry them out.
- An error in one request returns a JSON error; it never stops the server.
"""
from __future__ import annotations

import datetime as dt
import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, unquote, urlsplit

from . import projection
from .central_log import CentralLog
from .config import HOST, Config
from .events import Watcher, fingerprint
from .sources import WATCHED, event_log, ledger
from .sources.common import NOT_TRACKED, file_mtime, unavailable

MAX_BODY = 64 * 1024
MAX_INGEST_BODY = 1024 * 1024
SOURCE_NAME = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
SSE_KEEPALIVE = 15.0

# Commands the UI may send, per resource collection. See gui/README.md.
COMMANDS = {
    "decisions": {"approve", "reject", "requestRevision", "defer"},
    "findings": {"verify", "reject"},
    "opportunities": {"approve", "reject", "merge", "requestRevision", "defer"},
    "runs": {"rerun", "pause", "resume", "stop"},
    "egress/approvals": {"approve", "revoke"},
    "data/intakes": {"approve", "reject"},
}
COMMAND_PATH = re.compile(r"^/api/(decisions|findings|opportunities|runs|egress/approvals|data/intakes)/([^/:]+):([A-Za-z]+)$")
NOT_TRACKED_PATHS = re.compile(r"^/api/(opportunities|campaigns|egress)(/[^/]+)?$|^/api/sessions/[^/]+$")

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class ApiError(Exception):
    def __init__(self, code: int, status: str, message: str) -> None:
        super().__init__(message)
        self.code, self.status, self.message = code, status, message


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, config: Config, watcher: Optional[Watcher] = None) -> None:
        self.config = config
        self.log = CentralLog(config.root / event_log.REL_PATH)
        self.watcher = watcher or Watcher(config.root, config.poll_seconds, before_check=self.import_sources)
        self.import_sources()
        super().__init__((HOST, config.port), Handler)

    def import_sources(self) -> None:
        """Copy new events from the configured external files into the central log."""
        for rel in self.config.event_files:
            try:
                self.log.import_file(self.config.root, rel)
            except OSError:
                pass  # an unreadable source is retried on the next check

    def shutdown(self) -> None:
        self.watcher.stop()
        super().shutdown()


class Handler(BaseHTTPRequestHandler):
    server: DashboardServer
    server_version = "AisocGui/1"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # ---------- plumbing ----------
    def log_message(self, fmt, *args):  # only server errors are logged
        if len(args) > 1 and str(args[1]).startswith("5") and str(args[1]) != "501":  # 501 = expected refusal
            super().log_message(fmt, *args)

    def _send(self, code: int, body: bytes, ctype: str, extra: Optional[dict] = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, err: ApiError) -> None:
        # The request body may not have been read; close the connection so it is never parsed as a new request.
        self.close_connection = True
        body = json.dumps({"error": {"code": err.code, "status": err.status, "message": err.message}}).encode("utf-8")
        self._send(err.code, body, "application/json; charset=utf-8", {"Connection": "close"})

    def _check_host(self) -> None:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        if host not in ("127.0.0.1", "localhost"):
            raise ApiError(403, "FORBIDDEN", "requests must be addressed to 127.0.0.1 or localhost")

    def _check_origin(self) -> None:
        origin = self.headers.get("Origin")
        if origin is None:
            return
        port = self.server.server_port
        allowed = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
        if origin not in allowed:
            raise ApiError(403, "FORBIDDEN", "cross-origin requests are not allowed")

    def _dispatch(self, fn) -> None:
        try:
            self._check_host()
            fn()
        except ApiError as err:
            self._error(err)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # noqa: BLE001 - one bad request never stops the server
            self.log_error("internal error: %r", exc)
            try:
                self._error(ApiError(500, "INTERNAL", "internal error"))
            except Exception:  # noqa: BLE001
                pass

    # ---------- verbs ----------
    def do_GET(self):
        self._dispatch(self._get)

    def do_HEAD(self):
        self._dispatch(self._get)

    def do_POST(self):
        self._dispatch(self._post)

    def _method_not_allowed(self):
        def refuse():
            raise ApiError(405, "METHOD_NOT_ALLOWED", "method not allowed")
        self._dispatch(refuse)

    do_PUT = do_PATCH = do_DELETE = _method_not_allowed

    # ---------- GET ----------
    def _get(self) -> None:
        url = urlsplit(self.path)
        path = unquote(url.path)
        query = parse_qs(url.query)
        root = self.server.config.root
        now = dt.datetime.now(dt.timezone.utc)

        if path == "/api/health":
            snap = {rel: file_mtime(root / rel) for rel in (*WATCHED, *self.server.config.event_files)}
            return self._json(200, {
                "schemaVersion": projection.SCHEMA_VERSION,
                "asOf": now.isoformat(timespec="seconds"),
                "fingerprint": fingerprint(snap),
                "sources": [{"path": k, "exists": v is not None, "mtime": v} for k, v in snap.items()],
            })
        if path == "/api/overview":
            return self._json(200, projection.build_overview(root, now))
        if path == "/api/project":
            return self._json(200, projection.build_project(root, now))
        if path == "/api/evidence":
            ov = projection.build_pipeline(root, projection.build_runs(root))
            return self._json(200, ov[0])
        if path == "/api/audit":
            runs = projection.build_runs(root)
            _, view, _ = projection.build_events(root, runs, now)
            return self._json(200, {"entries": projection.build_actions(runs, now, view)})
        if path == "/api/findings" or path.startswith("/api/findings/") or path == "/api/decisions" or path.startswith("/api/decisions/"):
            return self._from_events(path, query, root, now)
        if path == "/api/runs" or path.startswith("/api/runs/"):
            return self._runs(path, query, root, now)
        if path.startswith("/api/operations/"):
            raise ApiError(404, "NOT_FOUND", "no such operation")
        if path == "/api/events":
            return self._events()
        if NOT_TRACKED_PATHS.match(path):
            return self._json(200, NOT_TRACKED)
        if path.startswith("/api/"):
            raise ApiError(404, "NOT_FOUND", "no such endpoint")
        if path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        return self._static(path)

    def _runs(self, path: str, query: dict, root: Path, now: dt.datetime) -> None:
        runs = projection.build_runs(root)
        if not runs.ok:
            return self._json(200, unavailable(runs.reason))
        rows = runs.value
        parts = path.split("/")  # ['', 'api', 'runs', id?, 'log'?]
        if path == "/api/runs":
            status = (query.get("status") or [None])[0]
            mode = (query.get("mode") or [None])[0]
            out = []
            for r in rows:
                shown = projection.STATUS_MAP.get(r.get("status", ""))
                if status and shown != status:
                    continue
                if mode and r.get("mode") != mode:
                    continue
                out.append(dict(r, displayStatus=shown))
            return self._json(200, {"runs": out})
        run_id = parts[3] if len(parts) > 3 else ""
        row = next((r for r in rows if r["run_id"] == run_id), None)
        if row is None:
            raise ApiError(404, "NOT_FOUND", "no such run")
        if len(parts) == 4:
            return self._json(200, dict(row, displayStatus=projection.STATUS_MAP.get(row.get("status", ""))))
        if len(parts) == 5 and parts[4] == "log":
            log = ledger.log_path(root, run_id, rows)
            if log is None:
                raise ApiError(404, "NOT_FOUND", "no log for this run")
            return self._send(200, log.read_bytes(), "application/x-ndjson; charset=utf-8")
        raise ApiError(404, "NOT_FOUND", "no such endpoint")

    def _from_events(self, path: str, query: dict, root: Path, now: dt.datetime) -> None:
        overview = projection.build_overview(root, now)
        kind = path.split("/")[2]
        if kind == "findings":
            items = overview["findings"]
            if not isinstance(items, list):
                return self._json(200, items)  # not tracked or unavailable
            verification = (query.get("verification") or [None])[0]
            items = [f for f in items if not verification or f["verification"] == verification]
        else:
            if overview["decisions"].get("tracked") is False or overview["decisions"].get("available") is False:
                return self._json(200, overview["decisions"])
            items = [w for w in overview["work"] if w.get("resource", "").startswith("decisions/")]
        parts = path.split("/")
        if len(parts) == 3:
            return self._json(200, {kind: items})
        match = next((i for i in items if i["id"] == parts[3]), None) if len(parts) == 4 else None
        if match is None:
            raise ApiError(404, "NOT_FOUND", f"no such {kind[:-1]}")
        return self._json(200, match)

    def _static(self, path: str) -> None:
        web = self.server.config.web_root.resolve()
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (web / rel).resolve()
        try:
            target.relative_to(web)
        except ValueError:
            raise ApiError(404, "NOT_FOUND", "not found") from None
        if not target.is_file():
            raise ApiError(404, "NOT_FOUND", "not found")
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "text/javascript"):
            ctype += "; charset=utf-8"
        extra = {"Content-Security-Policy": CSP} if target.suffix == ".html" else None
        self._send(200, target.read_bytes(), ctype, extra)

    # ---------- event stream ----------
    def _events(self) -> None:
        watcher = self.server.watcher
        try:
            last = int(self.headers.get("Last-Event-ID") or 0)
        except ValueError:
            last = 0
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        start = watcher.last_id
        self.wfile.write(f"retry: 3000\nid: {start}\nevent: hello\ndata: {json.dumps({'type': 'hello'})}\n\n".encode())
        self.wfile.flush()
        last = max(last, start)
        while not watcher.stopped:
            events = watcher.wait_after(last, SSE_KEEPALIVE)
            if not events:
                self.wfile.write(b": keep-alive\n\n")
            for eid, etype in events:
                self.wfile.write(f"id: {eid}\nevent: {etype}\ndata: {json.dumps({'type': etype})}\n\n".encode())
                last = eid
            self.wfile.flush()

    # ---------- POST (commands) ----------
    def _post(self) -> None:
        self._check_origin()
        path = unquote(urlsplit(self.path).path)
        if path == "/api/logs":
            return self._ingest()
        self._body = None
        try:
            self._command(path)
        except ApiError as err:
            self._log_interaction(path, err)
            raise

    def _log_interaction(self, path: str, err: ApiError) -> None:
        """Every command sent from the dashboard goes into the central log, with the reply it got."""
        body = self._body if isinstance(self._body, dict) else {}
        entry = {"command": path[len("/api/"):] if path.startswith("/api/") else path,
                 "actor": self.server.config.actor,
                 "outcome": {"code": err.code, "status": err.status, "message": err.message}}
        for key in ("requestId", "expectedVersion", "into"):
            if key in body:
                entry[key] = body[key]
        if isinstance(body.get("rationale"), str):
            entry["rationale"] = body["rationale"][:2000]
        try:
            self.server.log.add_interaction(entry)
            self.server.watcher.check()
        except OSError:
            pass

    def _ingest(self) -> None:
        """POST /api/logs: an external source hands events to the dashboard's central log."""
        body = self._read_json(MAX_INGEST_BODY)
        source = body.get("source")
        if not isinstance(source, str) or not SOURCE_NAME.match(source):
            raise ApiError(400, "BAD_REQUEST", "source must be a short name (letters, digits, _ . : -)")
        events = body.get("events")
        if not isinstance(events, list) or not events:
            raise ApiError(400, "BAD_REQUEST", "events must be a non-empty list")
        result = self.server.log.add_events(f"api:{source}", events)
        self.server.watcher.check()
        self._json(200, result)

    def _command(self, path: str) -> None:
        m = COMMAND_PATH.match(path)
        if m:
            collection, target_id, action = m.groups()
        elif path == "/api/egress:pauseAll":
            collection, target_id, action = "egress", "", "pauseAll"
        else:
            raise ApiError(404, "NOT_FOUND", "no such command")
        if collection != "egress" and action not in COMMANDS[collection]:
            raise ApiError(404, "NOT_FOUND", f"{collection} has no action '{action}'")

        body = self._body = self._read_json()
        rationale = body.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ApiError(400, "RATIONALE_REQUIRED", "a non-empty rationale is required")
        if not isinstance(body.get("expectedVersion"), int) or isinstance(body.get("expectedVersion"), bool):
            raise ApiError(400, "BAD_REQUEST", "expectedVersion must be an integer")
        if not isinstance(body.get("requestId"), str) or not body["requestId"].strip():
            raise ApiError(400, "BAD_REQUEST", "requestId is required")
        if action == "merge" and not isinstance(body.get("into"), str):
            raise ApiError(400, "BAD_REQUEST", "merge needs 'into'")

        if collection == "runs":
            root = self.server.config.root
            runs = projection.build_runs(root)
            known = {r["run_id"] for r in runs.value} if runs.ok else set()
            log = event_log.read(root)
            if log.ok:
                known |= {e["subject"]["id"] for e in log.value["events"] if e["subject"]["type"] == "run"}
            if runs.ok and target_id not in known:
                raise ApiError(404, "NOT_FOUND", "no such run")
        raise ApiError(501, "UNSUPPORTED", "no control plane can carry out this command yet (#6)")

    def _read_json(self, limit: int = MAX_BODY) -> dict:
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise ApiError(400, "BAD_REQUEST", "Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "BAD_REQUEST", "bad Content-Length") from None
        if length > limit:
            raise ApiError(413, "PAYLOAD_TOO_LARGE", "request body too large")
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "BAD_REQUEST", "body is not valid JSON") from None
        if not isinstance(data, dict):
            raise ApiError(400, "BAD_REQUEST", "body must be a JSON object")
        return data


def serve(config: Config) -> None:
    server = DashboardServer(config)
    server.watcher.start()
    print(f"AISoc dashboard: http://{HOST}:{config.port}/  (reading {config.root}; Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.watcher.stop()
        server.server_close()
