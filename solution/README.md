# Solution

This folder holds the Product Requirements Document (`PRD.md`) for the proposed solution, and later the solution application itself.

**Green-light gate.** No application code is written here until the researcher green-lights `PRD.md`. Before that, this folder holds `PRD.md` and planning documents only. The harness test suite fails if application code appears under `solution/` before green-light. When green-lit, the app is added as a **submodule** under `solution/` and gets its own architecture and tests inside that submodule.
