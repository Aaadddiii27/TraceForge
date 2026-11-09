# Project Task Tracker

| Milestone | Scope | Status |
|---|---|---|
| 1 | Repository foundation, architecture, documentation | Implemented |
| 2 | FastAPI backend, tools, providers, persistence, runtime | Implemented in source; runtime tests need local dependencies |
| 3 | Evaluation datasets, execution, metrics, comparison, exports | Implemented in source; runtime tests need local dependencies |
| 4 | React dashboard, navigation, API integration | Implemented in source; frontend build not verified in this environment |
| 5 | Prometheus, optional OpenTelemetry, trace collection, Grafana | Configuration and source implemented; runtime verification pending |
| 6 | Docker Compose, CI, Windows startup scripts, operational docs | Configured; Docker validation pending |
| 7 | Final local integration and release verification | Pending local execution |
| 8 | AWS deployment and production hardening | Not started; requires explicit cloud/account configuration |

## Current next actions

- On Windows, start Docker Desktop and run `scripts/windows/start.ps1`.
- Resolve any dependency/build issues reported by Docker Compose.
- Verify the dashboard task/evaluation workflows against the running API.
- Run the test commands documented in README.md.
- Update this tracker with actual local results; do not mark unexecuted checks as passed.
