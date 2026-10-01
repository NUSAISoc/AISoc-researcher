# Workflow records

This directory holds current lifecycle records under `records/`, prior revisions under `history/records/`, reviewed change receipts under `history/changes/`, and the generated `manifest.json`. No study evidence or lifecycle records are invented to initialize the harness. The empty manifest is intentional.

See the [workflow control contract](../00-research-workflow-controls.md) for the approved lifecycle, ownership, and retention rules. Readable records begin with a fenced JSON metadata block, followed by prose. The manifest is generated, not edited independently.

```bash
python3 -m workflow check
python3 -m workflow manifest
python3 -m workflow rebuild
```

`check` validates the files and exact revision links, then checks index parity. `manifest` prints the derived index without mutation. `rebuild` writes the derived index. Proposed record changes must preserve IDs and creation dates, increment revisions by one, and use allowed transitions. Human approval is checked separately when applying a proposal; an approved status alone is not proof of authorization.
