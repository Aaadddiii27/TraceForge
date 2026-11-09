# AI Runtime & Evaluation Platform

A self-hostable developer platform for executing AI-assisted tasks, inspecting tool-level traces, running repeatable evaluations, and observing runtime reliability. The default local provider is deterministic and requires no paid model API key.

## What is included

- **Runtime API:** FastAPI task submission, tool registry, provider abstraction, execution steps, retry/timeout handling, and persisted task history.
- **Built-in tools:** calculator, safe text processor, local knowledge-base lookup, and deterministic mock tool.
- **Evaluation:** versioned datasets, deterministic assertions, benchmark runs, per-case results, CSV export, run comparison, and regression detection.
- **Dashboard:** React + TypeScript pages for overview, executions, execution details, evaluations, datasets, run details, comparisons, tools, observability, and system health.
- **Observability:** Prometheus metrics, optional OpenTelemetry instrumentation, OTLP Collector, Jaeger trace UI, and Grafana dashboard provisioning.
- **Local infrastructure:** Docker Compose with PostgreSQL, Redis, API, frontend, Prometheus, Grafana, OpenTelemetry Collector, and Jaeger.

## Quick start (Windows)

Prerequisites: Docker Desktop running with the Docker Compose plugin.

1. Extract this repository.
2. Open PowerShell in the project root.
3. Run:

```powershell
.\scripts\windows\start.ps1
```

The script creates `.env` from `.env.example` if needed and starts the stack. Review `.env` before using the system beyond local development.

Open:

| Service | URL | Local credentials |
|---|---|---|
| Dashboard | http://localhost:3000 | No login in local-development mode |
| FastAPI docs | http://localhost:8000/docs | No login in local-development mode |
| Prometheus | http://localhost:9090 | No login |
| Grafana | http://localhost:3001 | `admin` / `GRAFANA_ADMIN_PASSWORD` from `.env` (default `localdevpassword`) |
| Jaeger traces | http://localhost:16686 | No login |

Stop the services without deleting data:

```powershell
.\scripts\windows\stop.ps1
```

To remove containers and persistent database/monitoring volumes as well (destructive to local stored data):

```powershell
docker compose down -v
```

## Run without Docker (development)

You need Python 3.11+, Node.js 20+, PostgreSQL, and Redis.

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
$env:DATABASE_URL="postgresql+asyncpg://ai_runtime_user:localdevpassword@localhost:5432/ai_runtime"
$env:REDIS_URL="redis://localhost:6379/0"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (in another terminal):

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server runs at http://localhost:3000 and proxies `/api` requests to http://localhost:8000.

## Example API usage

Submit a calculator task:

```powershell
$body = @{ tool_ids = @("calculator"); input_payload = @{ expression = "(19 * 7) + 5" }; model_provider = "mock" } | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/tasks -ContentType "application/json" -Body $body
```

Useful endpoints:

- `GET /api/v1/health` — process liveness.
- `GET /api/v1/health/ready` — database and Redis readiness.
- `GET /api/v1/metrics` — Prometheus exposition.
- `GET/POST /api/v1/tasks` — task history and task execution.
- `GET /api/v1/tasks/{task_id}/steps` — execution steps.
- `GET /api/v1/tools` — registered tools.
- `GET /api/v1/evaluation/datasets` — datasets.
- `POST /api/v1/evaluation/runs` — run a dataset evaluation.
- `GET /api/v1/evaluation/runs/{run_id}` — run results.
- `GET /api/v1/evaluation/runs/{run_id}/compare/{other_run_id}` — compare runs.

## Configuration

Copy `.env.example` to `.env`. The platform uses the `mock` provider by default. OpenAI and Gemini adapters are optional and require installing the corresponding optional backend dependency and supplying a key. Never commit `.env` or credentials.

OpenTelemetry is optional. The Compose stack enables the OTLP collector integration and sends traces to Jaeger. For a backend-only development run, `OTEL_ENABLED=false` is a safe default. The collector's debug exporter logs trace summaries; Jaeger provides the trace UI.

## Tests and quality checks

Backend:

```powershell
cd backend
pip install -e ".[dev]"
pytest
ruff check app tests
ruff format --check app tests
```

Frontend:

```powershell
cd frontend
npm install
npm run lint
npm run type-check
npm test
npm run build
```

Integration tests require the configured PostgreSQL and Redis services. Docker builds require network access to retrieve base images and package dependencies. Run these checks in your local development environment before publishing a release.

## Repository structure

```text
backend/                 FastAPI application, services, models, migrations, tests
frontend/                React + TypeScript dashboard
scripts/                 Database and Windows startup helpers
deployment/              Prometheus, Grafana, and OpenTelemetry configuration
docs/                    Evaluation and architecture documentation
.github/workflows/       CI pipeline
docker-compose.yml       Local multi-service environment
```

## Security and production notes

This project is configured for local development. Authentication is disabled by default, and the Compose ports are intended for a trusted local machine. Do not expose the stack directly to the public internet. Before production use, enable an authentication layer, replace all development secrets, restrict network ingress, configure TLS, secure Grafana/Prometheus/Jaeger, review payload retention and logging, and set up backups and alerting. See [SECURITY.md](SECURITY.md).

## Current implementation status

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for implemented components and validation limitations. Do not treat unexecuted tests or unverified deployment as passed.

## License

MIT — see [LICENSE](LICENSE).
