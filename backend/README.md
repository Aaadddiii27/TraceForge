# AI Runtime Backend

FastAPI service for deterministic task execution, tool orchestration, evaluation runs, and telemetry. Install from this directory with `pip install -e ".[dev]"` and start with `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.

The default provider is `mock`; external provider credentials are optional. PostgreSQL and Redis are expected for the complete local stack. See the repository root README for Docker Compose instructions.
