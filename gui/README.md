# AISoc Researcher GUI

The researcher dashboard. It shows the read model it is given and sends commands; it never edits research files or decides what research states mean. Design decisions live in [DESIGN.md](DESIGN.md).

Status: the overview screen and a local server exist. Served by the server, the dashboard shows real data from the repository files listed under [Data sources](#data-sources); everything else is shown as "not tracked yet". Opened from disk, or with `?adapter=mock`, it shows placeholder data from `web/js/mock-adapter.js`. Findings, decisions and running state come from events that other parts of the system send (see [Event input and the central log](#event-input-and-the-central-log)). Commands are validated, logged, and refused with `501 UNSUPPORTED` until the control plane (#6) can carry them out.

## Run it

Python 3.10 or newer, standard library only. From the repository root:

```bash
python3 -m gui.server            # http://127.0.0.1:8765
python3 -m gui.server --port 9000
```

The server only listens on `127.0.0.1` and only reads research files. The one file it writes is its own central log, `gui/.local/log.jsonl`, which stays on your machine and is not committed.

Without the server, open `gui/web/index.html` directly to see the mock data. Mock preview states: add `?state=loading`, `?state=stale`, `?state=disconnected` or `?state=new`. With the server running, add `?adapter=mock` to see the mock instead of real data.

## Tests

```bash
python3 -m unittest discover -s gui/tests -t .
```

They build throwaway repositories in temporary folders and never touch the real one. They cover each source reader, the overview (including that one broken file only affects its own section and that nothing is written), and the server end to end: contract shapes, localhost-only and cross-origin checks, path traversal, log access, command validation and the event stream. They are separate from the harness tests in `tests/`, so a GUI failure never blocks or changes those.

## Files

The parts are kept separate so a failure in one does not break the others:

```
gui/
  web/                  static UI; works without the server (mock data)
    index.html          page shell, confirmation dialog, toast
    css/styles.css      tokens, layout, components, responsive rules
    css/motion.css      all animation (remove its <link> to disable)
    js/icons.js         bundled icons: icon(name, extraClass)
    js/mock-adapter.js  placeholder data, same interface as the HTTP adapter
    js/http-adapter.js  talks to the local server
    js/app.js           rendering and interaction; picks an adapter
  server/               local server (python3 -m gui.server)
    sources/            one reader per source file; each fails on its own
    event_format.py     the event format the dashboard accepts
    central_log.py      the central log: imports event files, stores API events and interactions
    event_view.py       turns logged events and interactions into dashboard items
    projection.py       builds the read model; each section is built separately
    app.py              HTTP: routing, safety checks, commands, event input, event stream
    events.py           change detection for the event stream
    config.py           port, repository root, actor, event files
  contract/             JSON schemas for responses, commands, errors, events and log records
  tests/                GUI tests (separate from the harness tests)
  .gitignore            keeps .local/ (the central log) out of git
```

Local, not committed: `gui/.local/log.jsonl`, the central log (see [Event input and the central log](#event-input-and-the-central-log)).

## Data sources

There is no database. The server reads the repository files below, read-only, and checks their modification times every two seconds to push updates. `GET /api/health` reports which files were read and when. Anything not listed is not tracked yet and is shown as "not tracked yet".

| Source | Path | What is read | What it cannot tell us | Shown as |
| --- | --- | --- | --- | --- |
| Research question | `docs/03-research-question.md` | the quoted line under "The one main research question"; the template text `<Your one main research question goes here.>` means not set | anything else | header |
| Run ledger | `results/ledger.csv` | one row per run: `run_id`, `timestamp_utc`, `mode`, `experiment`, `config_hash`, `synthetic`, `num_records`, `status` (`ok` or `error`), `notes` | who started a run; campaign or hypothesis; progress while running; timeout, cancelled or inconclusive outcomes; the full configuration (only its hash) | runs, Problems (runs with `error`), Runs counts, Recent actions |
| Run logs | `results/logs/<run_id>.jsonl` | the log for a run, only for `run_id`s present in the ledger | | Log links |
| References | `references.md` | numbered entries under "All Readings Read So Far", counted by reading-depth tag (`[full]`, `[abstract]`, `[artifact]`, `[non-peer-reviewed]`); template entries in `<...>` are ignored | claims, contradictions | Evidence counts |
| Reading list | `readingList.md` | table rows, excluding the header and template rows | | Evidence "unread" |
| Result templates | `results/participants.csv`, `results/measurements.csv` | whether any row exists below the header | whether data was anonymised | Data ("No data yet" or "Has data") |
| Events | imported from `control/events.jsonl` (configurable) or sent to `POST /api/logs`, kept in `gui/.local/log.jsonl` | events in the dashboard's input format (see [Event input](#event-input-the-dashboards-hook)) | anything nobody sent | findings, decisions, running runs and their progress, run outcomes, Findings counts, Recent actions |

Findings and decisions are "not tracked yet" until the first event arrives. Not tracked yet, waiting for their owners: stage (#6); evidence claims, contradictions and opportunities (#7); campaigns and richer run outcomes (#9); agent sessions (agent harness); model traffic (model gateway); anonymisation status (anonymiser). When #6 provides its store, these file readers are replaced source by source; its format and location are not defined yet.

## How data reaches the UI

The UI talks to one adapter object and nothing else. `web/js/app.js` picks `AisocHttpAdapter` when served by the server, and `AisocMockAdapter` when opened from disk or with `?adapter=mock`. Both have the same interface:

| Member | Returns | Purpose |
| --- | --- | --- |
| `load()` | `Promise<overview read model>` | everything the overview displays |
| `sendCommand(resource, action, body)` | `Promise<{ ok: true, operation } \| { ok: false, status, message }>` | the only way to request a state change; see [Commands](#commands) |
| `subscribe({ onChange, onConnection })` | nothing | calls `onChange` when data changed and `onConnection('live' \| 'stale' \| 'disconnected')` |
| `actor` | `{ id, display }` | display only; the server records the real actor |

## API

Implemented by `gui/server`. The API follows command and query separation. Queries read projections that the GUI server builds from research files and received events, and can rebuild at any time. Commands are task-based requests that the GUI server forwards to the control-plane command contract owned by #6; the GUI never changes research state itself. Producers (agents, the experiment runner, the evidence pipeline, the model gateway) write through #6's interface, not through this API; what the dashboard needs from them is listed under [Events the dashboard needs](#events-the-dashboard-needs).

General rules:

- JSON over HTTP, served on `127.0.0.1` only. Requests whose `Host` header is not `127.0.0.1` or `localhost` are refused.
- Any field without a real source is returned as `{ "tracked": false }` and shown as "not tracked yet", never as zero.
- Errors use one shape: `{ "error": { "code": 409, "status": "VERSION_CONFLICT", "message": "..." } }`.
- The actor on a command is set by the server from its configuration, not taken from the request body.

### Queries

| Method and path | Returns | Source |
| --- | --- | --- |
| `GET /api/health` | `{ schemaVersion, asOf, sources: [{ path, mtime }] }` | server |
| `GET /api/overview` | the overview read model (below) | assembled from the queries below |
| `GET /api/project` | research question, stage, model traffic, data status | question from `docs/03-research-question.md`; data status from `results/participants.csv` and `results/measurements.csv`; stage and model traffic not tracked |
| `GET /api/runs` `?status=&mode=` | list of runs | `results/ledger.csv`; `status` is only `ok` or `error` until #9 records more outcomes; a `campaign` filter is added once runs record their campaign |
| `GET /api/runs/{id}` | one run | `results/ledger.csv` |
| `GET /api/runs/{id}/log` | the run's JSON Lines log | `results/logs/`, only for IDs present in the ledger |
| `GET /api/findings` `?verification=`, `GET /api/findings/{id}` | findings | received events; not tracked until the first event arrives |
| `GET /api/decisions`, `GET /api/decisions/{id}` | pending decisions, with what a review needs (summary, rationale, what it blocks) | received events; not tracked until the first event arrives |
| `GET /api/evidence` `?depth=&status=`, `GET /api/evidence/{id}` | sources | `references.md` depth tags and `readingList.md` |
| `GET /api/opportunities`, `GET /api/opportunities/{id}` | opportunity cards | not tracked |
| `GET /api/campaigns`, `GET /api/campaigns/{id}` | campaigns | not tracked |
| `GET /api/sessions/{id}` | agent session activity | not tracked |
| `GET /api/egress` | approvals, usage against limit, blocked requests | not tracked |
| `GET /api/audit` | recent audit entries, newest first | ledger rows (actor unknown), received events and dashboard interactions |
| `GET /api/operations/{name}` | one command operation | server |
| `GET /api/events` | server-sent event stream (below) | server |

List queries accept the filters shown so every pipeline count can link to a filtered list.

### Commands

Commands are `POST` requests to named actions on a resource, written with a colon. (`POST /api/logs` is not a command: it is how sources send events, see [Event input](#event-input-the-dashboards-hook).) Every command attempt is recorded in the central log with its reply.

| Resource | Actions |
| --- | --- |
| `/api/decisions/{id}` | `:approve`, `:reject`, `:requestRevision`, `:defer` |
| `/api/findings/{id}` | `:verify`, `:reject` |
| `/api/opportunities/{id}` | `:approve`, `:reject`, `:merge`, `:requestRevision`, `:defer` |
| `/api/runs/{id}` | `:rerun`, `:pause`, `:resume`, `:stop` |
| `/api/egress/approvals/{id}` | `:approve`, `:revoke` |
| `/api/egress` | `:pauseAll` |
| `/api/data/intakes/{id}` | `:approve`, `:reject` |

Request body:

```json
{
  "rationale": "required, non-empty, recorded in the audit trail",
  "expectedVersion": 3,
  "requestId": "client-generated unique id, so a repeated click is applied once"
}
```

`:merge` also takes `"into": "<id>"`.

If the command can start, the reply is `202` with an operation:

```json
{
  "name": "operations/op-17",
  "done": false,
  "metadata": { "command": "runs/R14:stop", "actor": "researcher-1", "requestedAt": "2026-09-28T14:30:00Z" }
}
```

The operation becomes `"done": true` with either `response` or `error` once the control plane has carried the command out. The UI shows the item as requested until then and never marks it done itself. Watch `operation.updated` events or poll `GET /api/operations/{name}`.

If the command cannot start, the reply is a normal error and no operation is created:

| Code | Status | When |
| --- | --- | --- |
| 400 | `RATIONALE_REQUIRED` | empty rationale |
| 404 | `NOT_FOUND` | unknown target |
| 409 | `VERSION_CONFLICT` | the target changed since the UI loaded it |
| 501 | `UNSUPPORTED` | no control plane can carry out this command yet (every command, until #6 exists) |
| 503 | `DISCONNECTED` | the control plane is unreachable |

Other errors the server returns: `400 BAD_REQUEST` (malformed body, wrong `Content-Type`, missing `expectedVersion` or `requestId`), `403 FORBIDDEN` (wrong `Host`, or a request from another web origin), `405 METHOD_NOT_ALLOWED`, `413 PAYLOAD_TOO_LARGE` (body over 64 KB). Error responses close the connection.

### Live updates

`GET /api/events` is a server-sent event stream (`contract/event.schema.json`). Every connection starts with a `hello` event; each message has an increasing `id`, an `event` type, and `data`:

```
id: 1042
event: run.updated
data: {"type": "run.updated"}
```

Types: `hello`, `project.updated`, `run.updated`, `evidence.updated`, `audit.appended`, and later `finding.updated`, `decision.updated`, `opportunity.updated`, `campaign.updated`, `egress.updated`, `operation.updated`. Today the server raises events when the source files change (`docs/03` and result templates: `project.updated`; `references.md` and `readingList.md`: `evidence.updated`; the ledger: `run.updated` and `audit.appended`; the central log, when events arrive or a command is logged: `finding.updated`, `decision.updated`, `run.updated` and `audit.appended`). It keeps events only in memory and does not replay missed ones; after reconnecting, the browser receives `hello` and re-fetches the overview. If the stream drops, the UI shows the stale state at once and the disconnected state after 15 seconds.

### Events the dashboard needs

To be provided by the control plane (#6) from its producers (#7, #9, the agent harness, the model gateway). Runs, findings, decisions and agent pauses can already be sent in the dashboard's input format; see [Event input](#event-input-the-dashboards-hook). Each event needs `id`, `type`, `at`, `actor: { kind: human | agent | system, id }` and `subject: { type, id, version }`.

| Event | Needed fields | Producer |
| --- | --- | --- |
| run started | campaign, hypothesis, protocol version, mode (synthetic or live), agent session, units total if known | #9 |
| run progressed | units recorded | #9 |
| run finished | outcome: success, failure, timeout, cancelled or inconclusive; log and artifact references; ledger row | #9 |
| finding inferred | claim, effect, uncertainty, source runs, synthetic flag, inferring session, harness and model | agents via #6 |
| finding evidence changed | what changed | #6 |
| decision proposed | kind, target, diff, rationale, what it blocks, proposing session | agents via #6 |
| decision, finding or opportunity decided | decision, rationale, human actor | #6 |
| command completed or failed | operation name, result or error | #6 |
| agent paused or resumed | reason | agent harness |
| evidence recorded | source, reading depth, claims, contradictions | #7 |
| opportunity proposed | the opportunity card fields | #7 |
| campaign state changed | new state, what blocks it | #9 |
| model request logged or blocked | provider, model, tokens, cost, approval | model gateway |
| data intake anonymised | script version, row counts, preview reference | anonymiser |

Urgency fields shown in the Work list (`paused`, `blocks`, `waitingSince`) must be derivable from these events.

## Event input and the central log

### Event input (the dashboard's hook)

The dashboard does not produce research data and does not decide whether it is true. Other parts of the system (agents, the experiment runner, the #6 control plane) send it events, and it shows them. There are two ways in; both accept the same format (`contract/event-log.schema.json`):

1. **An event file.** Append one JSON event per line to `control/events.jsonl` (the default; change it with `python3 -m gui.server --events <path>`, repeatable for several files). The server checks the files every two seconds and imports new complete lines. It never writes to these files.
2. **`POST /api/logs`** with `{"source": "<short name>", "events": [ ... ]}` (`contract/logs-request.schema.json`). The reply says how many events were accepted, how many were duplicates, and why any were rejected. Requests from other web origins are refused, like all other `POST`s.

An event:

```json
{"v": 1, "id": "e-1043", "type": "finding.inferred", "at": "2026-09-28T13:10:00Z",
 "actor": {"kind": "agent", "id": "s5"},
 "subject": {"type": "finding", "id": "F4", "version": 1},
 "data": {"claim": "...", "effect": "Inferred effect: ...", "uncertainty": "...", "synthetic": true}}
```

- `id` is unique per event; an event that arrives twice is stored once.
- `at` is UTC in the form `YYYY-MM-DDTHH:MM:SSZ`.
- `actor.kind` is `human`, `agent` or `system`.
- `subject.version` starts at 1 and increases by one per event for that subject; the dashboard sends the version it showed with every command.

Event types the dashboard displays, and the data fields it reads (all optional unless noted). Other types and fields are stored but not shown.

| Type | Data fields used | Shown as |
| --- | --- | --- |
| `run.started` | `experiment`, `mode` (`synthetic` or `live`), `campaign`, `unitsTotal`, `harness`, `model` | a running run in "In progress and recent" |
| `run.progressed` | `unitsRecorded`, `unitsTotal` | "3 of 8 units recorded" (a total is only shown when given) |
| `run.finished` | `outcome` (required): `success`, `failure`, `timeout`, `cancelled` or `inconclusive` | failures and timeouts under Problems, unless the run is already in the ledger |
| `finding.inferred` | `claim`, `effect` ("Inferred effect: ..."), `uncertainty`, `synthetic`, `campaign`, `harness`, `model`, `links` | an unverified finding under Needs your decision |
| `finding.evidence_changed` | `reason` | a verified finding becomes "re-check" |
| `finding.verified`, `finding.rejected` | `rationale` | the finding moves to Recent findings with who decided and why |
| `decision.proposed` | `kind`, `title`, `summary`, `rationale`, `blocks` (list of ids), `pausesAgent`, `campaign`, `hypothesis`, `harness`, `model`, `links` | a decision under Needs your decision; `blocks` and `pausesAgent` make it urgent |
| `decision.approved`, `decision.rejected`, `decision.revision_requested`, `decision.deferred` | `rationale` | settles or defers the decision |
| `agent.paused`, `agent.resumed` | `reason` | an entry in Recent actions |

One presentation safeguard: an event that verifies or rejects a finding, or settles a decision, is only shown as such if its actor is `human`. From an agent or system it is ignored and a warning is shown, so the dashboard can never make it look as if an agent approved something. Whether a `human` event really came from a person is the producer's responsibility (#6).

### The central log

Everything the dashboard receives or does is kept in one place: `gui/.local/log.jsonl`. It is local to the machine and not committed (`gui/.gitignore` lists `.local/`). Records are appended and never edited or removed (`contract/log-record.schema.json`):

| Kind | What |
| --- | --- |
| `event` | every well-formed event received, with its source (`file:control/events.jsonl` or `api:<name>`) |
| `invalid` | anything a source sent that was not a well-formed event, with the reason; reported as a warning |
| `interaction` | every command sent from the dashboard, with the reason given, the version it acted on, and the reply it got (today always `501 UNSUPPORTED`) |

Because imported events are copied here, the dashboard keeps showing them even if a source file is later rotated, rewritten or deleted. The dashboard reads only this log for findings, decisions, event-based runs and dashboard interactions; the research files listed under [Data sources](#data-sources) are read directly.

Limits: sources on the same machine are trusted (anything that can write the event file or reach `127.0.0.1` can send events); a source file rewritten in place beyond its first 4 KB without changing length is not detected as rewritten; the log has no rotation yet.

### For #6

The dashboard only needs events in the format above, from the event file, `POST /api/logs`, or both. How you store, validate, authorise and version research state is yours. If you move or rename the event file, start the server with `--events <path>` or change the default in `gui/server/config.py`. When you can carry out commands, the dashboard is ready to send them (see [Commands](#commands)).

## Overview read model

Top level: `schemaVersion`, `project`, `pipeline`, `work`, `findings`, `decisions`, `actions`, `warnings` (plus `connection`, added by the adapter). The schema is `contract/overview.schema.json`. All strings are treated as untrusted and HTML-escaped before display.

Markers used anywhere a value can be missing:

- `{ "tracked": false }`: no source yet; shown as "not tracked yet" (or "–" for a count).
- `{ "tracked": true, "available": false, "reason": "..." }`: the source exists but could not be read; shown as "couldn't read: ..." without affecting other sections.
- `warnings`: problems worth showing, such as ledger statuses that were not shown; displayed as a banner.

### `connection`

`"live" | "stale" | "disconnected" | "loading"`. Controls the Updated field, banners and whether commands are sent.

### `project`

| Field | Type | Shown as |
| --- | --- | --- |
| `researchQuestion` | string or null | header title; null shows "Not set yet" with a link to `docs/03-research-question.md` |
| `stage` | string | Stage |
| `modelTraffic` | `{ mode: "provider", provider, limitUsedPct }` or `{ mode: "local" }` | Model traffic |
| `data` | `{ anonymisedOnly, empty? }` | Data |
| `asOf`, `lastKnown` | `"HH:MM"` | Updated |

### `pipeline`

Array of stages: `{ stage, icon, counts: [[label, value, tone?]] }`. `tone: "bad"` colours a non-zero count red. Each count links to the matching list.

### `work`

Array of work items. Section and order are derived from `status` and `urgency`.

| Field | Type | Meaning |
| --- | --- | --- |
| `id`, `version` | string, number | target identity; `version` is sent with commands so a changed target is rejected |
| `status` | `decision`, `failed`, `inconclusive`, `blocked`, `running`, `ok` | label and section |
| `type` | string, optional | `finding` adds a "finding" label |
| `title`, `summary` | string | row text |
| `ids` | string | short IDs next to the title (hidden on phones) |
| `urgency` | `{ paused, blocks, waitingHours }` | ordering and the urgent marker; must come from the contract |
| `experiment`, `agent` | string arrays | Experiment and Agent lines in detailed view |
| `details` | `[[label, value]]` | shown when the row is expanded |
| `actions` | `review`, `rerun`, `pause`, `stop` | which buttons appear |
| `resource` | string, optional | path used for commands, e.g. `runs/R14`; without it no command buttons appear |
| `links` | strings, or `{ label, href }` | links under the buttons; `href` must be a same-origin path such as `/api/runs/{id}/log`, anything else is ignored |
| `pendingOperation` | `{ name, done, command }`, optional | shows "requested, waiting for control plane" until `done` |
| `synthetic` | boolean, optional | shows "synthetic, not reportable" |

Sections: `decision` goes to Needs your decision; `failed`, `inconclusive` and `blocked` go to Problems; `running` and `ok` go to In progress and recent.

### `findings`

| Field | Type | Meaning |
| --- | --- | --- |
| `id`, `version` | string, number | identity |
| `verification` | `unverified`, `recheck`, `verified`, `rejected` | unverified and recheck are shown as decisions; verified and rejected in Recent findings |
| `claim`, `effect`, `uncertainty` | string | text; `effect` is written as "Inferred effect: ..." |
| `inferredBy` | `{ session, agent, model, at }` | agent attribution |
| `reviewedBy` | `{ verb, name, at, rationale }`, optional | human attribution |
| `recheckReason` | string, optional | why a verified finding needs checking again |
| `ids`, `waitingHours`, `synthetic`, `links` | | as for work items |

### `actions`

Recent audit entries, newest first: `{ at, actor: { kind: "human" | "agent" | "system", name }, what, context?, rationale? }`.

## Adding things to the UI

Most additions need only data. UI code changes go in `web/js/app.js` unless noted.

| To add | Do this |
| --- | --- |
| A work item | Add an object to `work` with a `status`, `urgency`, `actions` and `links`. It is placed and sorted automatically. |
| A finding | Add to `findings` with `verification` and `inferredBy`; add `reviewedBy` once reviewed. |
| A pipeline count | Add `[label, value]` to a stage's `counts`, or a new stage object. |
| A header field | Add it to `build_project()` in `server/projection.py` and to `contract/overview.schema.json`, then render it in `renderHeader()`. |
| A status | Add an entry to `STATUS` (label, abbreviation, icon, CSS class), add it to `ORDER` and to a section in `SECTIONS`, and add colours for the class in `css/styles.css`. |
| A button or command | The command must exist in the Commands table (agree new ones with #6) and in `COMMANDS` in `server/app.py`. Add a branch in `actionButtons()` and dialog text in `CMD_TEXT` in `web/js/app.js`. State-changing commands must use the confirmation dialog. |
| An icon | Add a path to `js/icons.js`, then use `icon('name')`. |
| A new block on the page | Write a `renderX(view)` function and add it to `render()` in the main column or the side column. |
| An animation | Add it to `web/css/motion.css` only. |
| A new data source | Add one reader in `server/sources/` that returns a `SourceResult` and never raises, list its file in `sources/__init__.py`, use it in `projection.py`, and add tests in `gui/tests/`. |

Rules:

- Escape every value from the read model with `esc()`.
- Do not compute research meaning in the UI (status, urgency, outcome, verification). If you need a value, add it to the read model.
- Keep UI-only state in `ui` (filters, expanded rows, detailed view). Never store research state in the browser.
- Check desktop, tablet (744 to 1100 px) and phone (360 to 600 px) widths, the mock preview states, and the live server, after a change. Run the GUI tests.
