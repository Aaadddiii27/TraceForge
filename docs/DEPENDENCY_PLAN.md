# Dependency and Tooling Plan
# AI Runtime & Evaluation Platform

## Python / Backend

### Runtime Dependencies (pinned in pyproject.toml)

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.115.5 | Web framework — async, OpenAPI built-in |
| uvicorn[standard] | 0.32.1 | ASGI server with uvloop + httptools |
| python-multipart | 0.0.18 | Form data support |
| pydantic | 2.10.3 | Data validation and serialization |
| pydantic-settings | 2.6.1 | Settings from env vars |
| sqlalchemy | 2.0.36 | ORM — async-first, typed |
| alembic | 1.14.0 | Database migrations |
| asyncpg | 0.30.0 | Async PostgreSQL driver |
| psycopg2-binary | 2.9.10 | Sync driver for Alembic |
| redis | 5.2.1 | Redis client (async) |
| hiredis | 3.1.0 | Fast Redis parser |
| httpx | 0.28.1 | Async HTTP client (provider calls + tests) |
| opentelemetry-api | 1.29.0 | OTel instrumentation API |
| opentelemetry-sdk | 1.29.0 | OTel SDK |
| opentelemetry-instrumentation-fastapi | 0.50b0 | Auto-instrument FastAPI |
| opentelemetry-instrumentation-sqlalchemy | 0.50b0 | Auto-instrument SQLAlchemy |
| opentelemetry-exporter-otlp-proto-grpc | 1.29.0 | Export to OTel collector |
| prometheus-client | 0.21.1 | Prometheus metrics |
| python-dotenv | 1.0.1 | Load .env files |
| structlog | 24.4.0 | Structured logging |
| anyio | 4.7.0 | Async primitives |
| tenacity | 9.0.0 | Retry logic |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 8.3.4 | Test runner |
| pytest-asyncio | 0.24.0 | Async test support |
| pytest-cov | 6.0.0 | Coverage reporting |
| factory-boy | 3.3.1 | Test factories |
| faker | 33.1.0 | Fake data generation |
| ruff | 0.8.4 | Linting + formatting |
| mypy | 1.13.0 | Static type checking |

### Optional Provider Dependencies

| Package | Version | Condition |
|---------|---------|---------|
| openai | 1.57.4 | OPENAI_API_KEY set |
| google-generativeai | 0.8.3 | GEMINI_API_KEY set |

## Node / Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.x | UI framework |
| react-dom | 18.x | DOM rendering |
| typescript | 5.x | Type safety |
| vite | 5.x | Build tool + dev server |
| react-router-dom | 6.x | Client-side routing |
| axios | 1.x | HTTP client |
| @tanstack/react-query | 5.x | Server state management, caching |
| recharts | 2.x | Charting library (composable) |
| zustand | 5.x | Lightweight global state |
| @radix-ui/react-* | latest | Accessible headless UI primitives |
| tailwindcss | 3.x | Utility CSS |
| clsx | 2.x | Class name utility |
| date-fns | 3.x | Date formatting |
| vitest | 2.x | Fast unit test runner |
| @testing-library/react | 16.x | Component testing |
| eslint | 9.x | Linting |
| prettier | 3.x | Formatting |

## Infrastructure

| Tool | Version | Purpose |
|------|---------|---------|
| PostgreSQL | 16 (Alpine) | Primary database |
| Redis | 7 (Alpine) | Task queue, caching, pub/sub |
| Prometheus | 2.55.1 | Metrics collection |
| Grafana | 11.4.0 | Metrics visualization |
| nginx | 1.27 (Alpine) | Frontend static file serving |
| Docker | 29.x | Containerization |
| Docker Compose | v5.x | Local orchestration |

## Version Compatibility Notes

- Python 3.11 is used (not 3.14 which is installed) for maximum ecosystem compatibility.
  The host has 3.14, but Docker images pin 3.11-slim. Local dev can use either.
  SQLAlchemy 2.0 requires Python 3.7+. FastAPI 0.115+ requires Python 3.8+.
- asyncpg 0.30.0 supports PostgreSQL 9.6+ and Python 3.8+.
- OTel 0.50b0 beta packages match the 1.29.0 stable API packages.
- All frontend packages are React 18 compatible.

## Security Policy for Dependencies

1. Pin all direct dependencies to exact versions in pyproject.toml.
2. Allow minor updates for indirect deps via ranges.
3. Run `pip-audit` and `npm audit` in CI to detect known vulnerabilities.
4. Use Dependabot (GitHub) for automated PR-based dependency updates.
5. Never install packages with `--no-deps` or skip hash verification.
