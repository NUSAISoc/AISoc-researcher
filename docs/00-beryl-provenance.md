# Beryl Control-Plane Provenance

This document records which Beryl release governs this repository and how it was established. It exists so the control plane is reproducible and so a moving `main` branch can never silently change the project's gates.

## Pinned Source

| Field | Value |
| --- | --- |
| Repository | `https://github.com/Praneeth-Suresh/Beryl` |
| Tag | `v0.1.0` |
| Commit | `a0f5f51fbd21cb629622978358756a157df47b0e` |
| Installer version | `1` |
| Profile | `full` (`agent-core`, `tool-shims`, `checks`, `githooks`, `ci`, `driver`) |

## How This Control Plane Was Established

The Beryl control plane was seeded from the verified pinned install in the sibling `SocraticLLM` repository, which installed Beryl `v0.1.0` at commit `a0f5f51fbd21cb629622978358756a157df47b0e` (itself seeded from `BlueRedResearch`, where the archive SHA-256 was verified before staging). The `.beryl/` tree, `lock.json`, and root shims were copied so this repository is governed by the identical, pinned control plane. The lockfile's `sourceRef` records the pinned commit, and this document re-states it so the pin is discoverable from this repository alone. Seeding from a verified sibling is the documented method those repositories used, and it keeps the entire lab on one pinned control plane.

## Adaptations For This Project

This repository is a **generalized, forkable autoresearch harness**, not the specific study any sibling was built for. The following deliberate adaptations were made after seeding:

- **Skills.** Three writing and research-practice skills are installed under `.beryl/agent/skills/`: `academic-research-writer`, `voice-and-confidence-calibration`, and `clearly-and-concisely-academic`. They were ingested with `.beryl/agent/scripts/add-skill.sh` and registered in `task-routing.md` and `tool-instruction-template.md`; the shims were regenerated with `sync-agent-env.sh`.
- **Agent memory.** `.beryl/agent/project-brief.md`, root `RESEARCH_RULES.md`, `.beryl/agent/task-routing.md`, `.beryl/agent/synchronization-contract.md`, `.beryl/agent/systems-thinking-methodology.md`, `.beryl/agent/architecture.md`, `.beryl/agent/ubiquitous-language.md`, and `.beryl/agent/design-tree.md` were rewritten as generalized, placeholder-based templates: one research question at a time, no fabricated data, the green-light gate before building the solution app, file-boundary synchronisation, the autoresearch sandbox gate, and the human-at-the-centre rule.
- **Autoresearch harness.** An `experiments/` sandboxed runner, an `analysis/` package, and a `results/` ledger were added so a fork can run experiments automatically and reproducibly. See `experiments/README.md`.
- **Git hooks.** Not enabled by default, matching the sibling repositories. The gate is run explicitly as `./.beryl/scripts/check.sh` before each commit.

## Re-Verification

```bash
python3 -c "import json;d=json.load(open('.beryl/lock.json'));print(d['sourceRef'])"
./.beryl/scripts/check.sh
python3 -m unittest discover -s tests -t .
```
