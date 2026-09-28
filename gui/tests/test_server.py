"""The HTTP server end to end, on a random localhost port, against a throwaway repository."""
import http.client
import json
import os
import socket
import threading
import time
import unittest
from pathlib import Path

from gui.server.app import DashboardServer
from gui.server.config import WEB_ROOT, Config
from gui.tests import schema_check
from gui.server.central_log import read_records
from gui.server.sources import event_log
from gui.tests.fixtures import LEDGER_HEADER, event, make_repo, snapshot, write_events
from gui.tests.test_sources import ROW_ERR, ROW_OK

RUN_OK = "20260928T010000-synthetic-aaaa1111"
BODY = {"rationale": "testing", "expectedVersion": 1, "requestId": "r1"}


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.root = make_repo(**{"results/ledger.csv": LEDGER_HEADER + ROW_OK + ROW_ERR})
        (cls.root / "results/logs" / f"{RUN_OK}.jsonl").write_text('{"unit_index": 0}\n')
        cls.server = DashboardServer(Config(root=cls.root, web_root=WEB_ROOT, port=0, poll_seconds=0.1))
        cls.port = cls.server.server_port
        cls.server.watcher.start()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.before = snapshot(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def req(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": f"127.0.0.1:{self.port}"}
        h.update(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=data, headers=h)
        res = conn.getresponse()
        raw = res.read()
        conn.close()
        try:
            return res.status, json.loads(raw), res
        except ValueError:
            return res.status, raw, res

    def assertErr(self, status, body, code, name):
        self.assertEqual(status, code, body)
        self.assertEqual(schema_check.errors(body, schema_check.load("error.schema.json")), [])
        self.assertEqual(body["error"]["status"], name)

    # ---------- reads ----------
    def test_health_and_overview_match_contract(self):
        s, body, _ = self.req("GET", "/api/health")
        self.assertEqual(s, 200)
        self.assertEqual(schema_check.errors(body, schema_check.load("health.schema.json")), [])
        s, body, _ = self.req("GET", "/api/overview")
        self.assertEqual(s, 200)
        self.assertEqual(schema_check.errors(body, schema_check.load("overview.schema.json")), [])

    def test_runs_and_logs(self):
        s, body, _ = self.req("GET", "/api/runs?status=failed")
        self.assertEqual([r["status"] for r in body["runs"]], ["error"])
        s, body, _ = self.req("GET", f"/api/runs/{RUN_OK}/log")
        self.assertEqual(s, 200)
        self.assertIn(b"unit_index", body if isinstance(body, bytes) else json.dumps(body).encode())
        s, body, _ = self.req("GET", "/api/runs/nope/log")
        self.assertErr(s, body, 404, "NOT_FOUND")

    def test_not_tracked_endpoints(self):
        for path in ("/api/campaigns", "/api/sessions/s4", "/api/egress", "/api/opportunities/O1"):
            s, body, _ = self.req("GET", path)
            self.assertEqual((s, body), (200, {"tracked": False}), path)

    def test_static_files_and_traversal(self):
        s, body, res = self.req("GET", "/")
        self.assertEqual(s, 200)
        self.assertIn("Content-Security-Policy", res.headers)
        for path in ("/../server/app.py", "/%2e%2e/server/app.py", "/js/../../server/app.py"):
            s, body, _ = self.req("GET", path)
            self.assertEqual(s, 404, path)

    def test_wrong_host_is_refused(self):
        s, body, _ = self.req("GET", "/api/health", headers={"Host": "evil.example:80"})
        self.assertErr(s, body, 403, "FORBIDDEN")

    # ---------- commands ----------
    def test_valid_command_is_unsupported_for_now(self):
        s, body, _ = self.req("POST", f"/api/runs/{RUN_OK}:stop", BODY)
        self.assertErr(s, body, 501, "UNSUPPORTED")

    def test_commands_are_logged_with_their_reply(self):
        s, body, _ = self.req("POST", "/api/findings/F1:verify", {"rationale": "checked", "expectedVersion": 1, "requestId": "req-9"})
        self.assertErr(s, body, 501, "UNSUPPORTED")
        recs = [r for r in read_records(self.root / event_log.REL_PATH) if r["kind"] == "interaction"]
        last = recs[-1]["entry"]
        self.assertEqual((last["command"], last["rationale"], last["outcome"]["code"], last["actor"]),
                         ("findings/F1:verify", "checked", 501, "researcher-1"))
        s, ov, _ = self.req("GET", "/api/overview")
        self.assertTrue(any(a["what"] == "Requested verify of F1" for a in ov["actions"]))

    def test_external_source_can_send_logs(self):
        ev = event("finding.inferred", "agent", "s9", "finding", "F77", 1, {"claim": "c"})
        s, res, _ = self.req("POST", "/api/logs", {"source": "agent-s9", "events": [ev, {"v": 9}]})
        self.assertEqual((s, res["accepted"], len(res["rejected"])), (200, 1, 1))
        s, lst, _ = self.req("GET", "/api/findings")
        self.assertIn("F77", [f["id"] for f in lst["findings"]])
        s, res, _ = self.req("POST", "/api/logs", {"source": "bad name!", "events": [ev]})
        self.assertErr(s, res, 400, "BAD_REQUEST")
        s, res, _ = self.req("POST", "/api/logs", {"source": "x", "events": [ev]}, headers={"Origin": "http://evil.example"})
        self.assertErr(s, res, 403, "FORBIDDEN")

    def test_runs_known_only_from_events_accept_commands(self):
        ev = event("run.started", "system", "runner", "run", "R-EV1", 1, {"experiment": "x"})
        self.req("POST", "/api/logs", {"source": "runner", "events": [ev]})
        s, body, _ = self.req("POST", "/api/runs/R-EV1:stop", {"rationale": "r", "expectedVersion": 1, "requestId": "q"})
        self.assertErr(s, body, 501, "UNSUPPORTED")

    def test_event_file_is_imported(self):
        write_events(self.root, [event("decision.proposed", "agent", "s4", "decision", "D5", 1, {"title": "Proposal"})])
        deadline = time.time() + 5
        while time.time() < deadline:
            s, lst, _ = self.req("GET", "/api/decisions")
            if isinstance(lst, dict) and "decisions" in lst and lst["decisions"]:
                break
            time.sleep(0.1)
        self.assertEqual([d["id"] for d in lst["decisions"]], ["D5"])
        self.__class__.before = snapshot(self.root)  # a producer changed the event file, on purpose

    def test_command_validation(self):
        s, body, _ = self.req("POST", f"/api/runs/{RUN_OK}:stop", dict(BODY, rationale="  "))
        self.assertErr(s, body, 400, "RATIONALE_REQUIRED")
        s, body, _ = self.req("POST", f"/api/runs/{RUN_OK}:stop", dict(BODY, expectedVersion="1"))
        self.assertErr(s, body, 400, "BAD_REQUEST")
        s, body, _ = self.req("POST", f"/api/runs/{RUN_OK}:explode", BODY)
        self.assertErr(s, body, 404, "NOT_FOUND")
        s, body, _ = self.req("POST", "/api/runs/unknown-run:stop", BODY)
        self.assertErr(s, body, 404, "NOT_FOUND")
        s, body, _ = self.req("POST", f"/api/runs/{RUN_OK}:stop", BODY, headers={"Content-Type": "text/plain"})
        self.assertErr(s, body, 400, "BAD_REQUEST")

    def test_cross_origin_post_is_refused(self):
        s, body, _ = self.req("POST", f"/api/runs/{RUN_OK}:stop", BODY, headers={"Origin": "http://evil.example"})
        self.assertErr(s, body, 403, "FORBIDDEN")
        s, body, _ = self.req("POST", f"/api/runs/{RUN_OK}:stop", BODY, headers={"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertErr(s, body, 501, "UNSUPPORTED")

    def test_errors_close_the_connection(self):
        # An unread request body must never be parsed as a second request.
        s, body, res = self.req("POST", f"/api/runs/{RUN_OK}:explode", BODY)
        self.assertEqual(res.getheader("Connection"), "close")

    def test_other_methods_refused(self):
        s, body, _ = self.req("PUT", "/api/overview", {})
        self.assertErr(s, body, 405, "METHOD_NOT_ALLOWED")

    # ---------- events ----------
    def test_event_stream_reports_ledger_change(self):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        sock.sendall(f"GET /api/events HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n\r\n".encode())
        buf = b""
        deadline = time.time() + 5
        while b"event: hello" not in buf and time.time() < deadline:
            buf += sock.recv(4096)
        self.assertIn(b"event: hello", buf)
        ledger = self.root / "results/ledger.csv"
        st = ledger.stat()
        os.utime(ledger, (st.st_atime, st.st_mtime + 5))  # change detected, content untouched
        self.__class__.before = snapshot(self.root)
        while b"event: run.updated" not in buf and time.time() < deadline:
            buf += sock.recv(4096)
        sock.close()
        self.assertIn(b"event: run.updated", buf)

    # ---------- safety ----------
    def test_zz_nothing_was_written(self):
        self.assertEqual(snapshot(self.root), self.before)


if __name__ == "__main__":
    unittest.main()
