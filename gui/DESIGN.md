# GUI design

Design decisions for the AISoc Researcher dashboard. For how to run it, where its data comes from, and how to add elements, see [README.md](README.md).

## Purpose and boundaries

The dashboard makes the iterative research process understandable and lets the researcher direct it. It owns presentation and interaction only. It does not define lifecycle semantics (#6), evidence or hypothesis generation (#7), experiment execution or provenance (#9), or community governance (#3, #10). Until those contracts exist it runs on a mock adapter.

Acceptance criteria it is designed against:

- A researcher can identify the current state, pending human decisions, failed or inconclusive work, and evidence provenance without reading repository internals.
- Every state-changing action goes through the canonical command contract and remains auditable.
- The UI does not invent progress, hide uncertainty, or bypass human approval.

## Principles

- **Human in the loop first.** Anything that needs the researcher is the most prominent thing on the page. Approve and reject happen only on a review page next to the evidence, never as a one-click action on the dashboard.
- **No invented progress.** Counts, not percentages. Progress is shown only against a known total. Missing data is shown as missing ("not tracked yet"), never as zero.
- **Uncertainty and negative results are visible.** Inconclusive work, rejected ideas and results with no meaningful effect are counted and shown with the same weight as positive ones.
- **Requested is not done.** After a command, the UI shows "requested, waiting for the control plane" until the control plane confirms the change.
- **Everything traceable.** Every claim and decision links to its evidence, run, agent session and approval.
- **The UI decides nothing about research meaning.** Status, urgency, verification and outcome categories come from the data contract; the UI only groups, sorts and labels them.

## Privacy and local-first

- Agents and the dashboard run locally by default. The dashboard server binds to `127.0.0.1`, loads no fonts or scripts from a CDN, and sends no telemetry.
- Anything leaving the machine requires human approval first and is logged. The model provider is the one approved remote destination, approved per project (provider, model, limit, expiry, rationale) and routed through a local gateway that blocks by default and logs every request. Exceptions interrupt the researcher.
- Research data is anonymised by a local deterministic script before anything else touches it. Raw data stays in a quarantine location outside the repository; no agent and no part of the dashboard reads it.
- Single user for the MVP. Every command still records its actor so multiple users can be added later.

## What the UI may store

Only display state that is safe to lose: preferences (the Detailed view switch, in browser storage), unsent drafts, "seen" markers and caches that can be rebuilt. The test: deleting it changes no research state, decision or audit record. "Seen" is not "reviewed": marking something reviewed is a command with a rationale.

The dashboard also keeps its own central log (`gui/.local/log.jsonl`, local and not committed): a copy of every event it received from other parts of the system and a record of every command sent from the interface with its reply. It is the dashboard's audit of what it was told and what was asked of it, not the research record; research state belongs to #6.

## Information hierarchy (overview)

Main column, top to bottom:

1. **Project header.** Research question, stage, model traffic (provider and share of limit, link to egress), data status, last update and connection state.
2. **Pipeline.** Counts per stage: evidence, opportunities, campaigns, runs, findings. Rejected and contradicted items are counted. Every count links to the matching list.
3. **Work.** Three collapsible sections in fixed order: Needs your decision, Problems, In progress and recent.

Side column: **Recent findings** (verified and rejected only) and **Recent actions** (audit excerpt with actor and rationale).

## Visual system

Dark mode first; light mode later. Scheme "B, lab notebook":

| Token | Value | Use |
| --- | --- | --- |
| background | `#141817` | page |
| surface | `#1B201F` | cards, boxes |
| text | `#E1E6E3` | primary text |
| muted | `#8E9994` | secondary text |
| rule | `#2C3432` | hairline borders |
| accent | `#7FB5A3` | links, primary buttons, focus |
| live | `#86C98F` | live connection indicator |

Avoid anything that reads as generic AI styling: corners of 2 to 4 px, 1 px hairlines instead of shadows, no gradients, glows or purple, one accent colour used sparingly. Type: IBM Plex Sans (or system sans) and IBM Plex Mono for IDs; no web fonts are downloaded.

## Status system

Work item statuses. Labels are the same width so row text aligns; each has an icon so colour is never the only cue.

| Status | Colour | Icon | Notes |
| --- | --- | --- | --- |
| decision | amber `#E8B75A` | alert | most prominent; section gets an amber left edge |
| failed | `#EE8A7E` | cross | |
| inconclusive | `#B8BCC2`, dashed border | question | abbreviated "inconcl."; full word for screen readers and on hover |
| blocked | `#A9B8C6` | lock | says what it is blocked by |
| running | `#7FB5A3` | loader | |
| ok | muted grey | tick | deliberately quiet |

Finding verification states: **unverified** (amber, dashed), **re-check** (amber; evidence changed after verification), **verified** (quiet grey), **rejected** (red, kept for the record). Unverified and re-check findings appear under Needs your decision with a "finding" type label and move back to Recent findings once cleared. Each finding shows who inferred it (agent session, harness, model, time) and who verified or rejected it, with their reason. Effects are described in plain language prefixed "Inferred effect"; there is no "null" label.

## Rows and actions

Row: status label, text column, actions column. Text column: title, expand chevron after the last word, urgent marker, short IDs, summary; in detailed view also an Experiment line and an Agent line.

Action styles, strongest to weakest:

1. Filled accent button with chevron ("Review ›"): needs the researcher, opens the review page.
2. Outlined button with icon (Rerun, Pause): routine, reversible.
3. Red outline (Stop): destructive, always confirms.
4. Link with chevron below the buttons ("Log ›", "Evidence ›"), right aligned, several links separated by " · " with one chevron.

Every state-changing action opens a confirmation dialog with a required reason that is recorded.

## Density, expansion, filtering, ordering

- **Detailed view switch** (off by default) adds the Experiment and Agent lines. Links stay visible either way.
- **Rows expand in place.** Clicking blank space expands; clicking text does not (so it can be selected); buttons and links keep their own actions. Enter and Space work from the keyboard.
- **Work sections collapse** from a chevron after the section title; the title and count stay visible.
- **Status filter** is one button ("Status: all / 4 of 6") opening a checkbox menu with counts. If decisions are hidden by the filter, an amber notice says so.
- **Urgency ordering** within each section: paused agents first, then by how much work an item blocks, then by waiting time. Urgent rows get an "urgent" marker. The urgency fields come from the data.

## States

Loading (plain placeholders, no shimmer), stale (amber banner, decisions still check the latest version before applying), disconnected (red banner, last known state kept, commands refused with a message), new project (explains what will appear).

## Responsive

| Width | Layout |
| --- | --- |
| over 1100 px | two columns |
| 601 to 1100 px (tablet portrait) | one column; findings and actions in a drawer opened from a tab on the right edge, with a count of findings to review |
| up to 600 px (phone) | header and pipeline become lines; status labels become icons (text kept for screen readers); urgent becomes an icon under the status; row actions sit on their own line aligned with the title; experiment and agent lines and short IDs are dropped; findings and actions open full screen from a floating button |

Touch screens get larger tap targets.

## Motion

All motion lives in `web/css/motion.css`; removing its link in `index.html` rolls it back completely. Timing follows IBM Carbon productive motion: standard curve for things that move and stay, entrance curve for things that appear, closing slightly faster than opening (rows and sections 240 ms open and 180 ms close, drawer 200 ms and 160 ms, menus 110 ms). Disabled when the system asks for reduced motion.

## Accessibility

Visible focus outlines; every control reachable by keyboard; expanded, collapsed, on and off states announced; icons decorative with text alternatives where they carry meaning; abbreviations and icon-only labels keep their full words for screen readers; status never relies on colour alone.

## Open questions

- Sorting decisions by blocking impact or by age (researcher interviews).
- Who supplies urgency fields (#6, #9).
- Light mode palette.
- Review page, run detail, evidence and provenance view, stage screens, egress panel, data intake: not designed yet.
- On touch screens, whether tapping a row's text should expand it.
