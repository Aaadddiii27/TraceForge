# Contributing

1. Create a feature branch from the current default branch.
2. Keep changes focused and update relevant documentation.
3. Backend changes: run `ruff check app tests`, `ruff format --check app tests`, and `pytest` from `backend/`.
4. Frontend changes: run `npm install`, `npm run lint`, `npm run type-check`, `npm test`, and `npm run build` from `frontend/`.
5. For API changes, keep Pydantic schemas, OpenAPI documentation, frontend types, and API client behavior aligned.
6. Never commit `.env`, credentials, database files, caches, coverage output, or generated build directories.
7. Include tests for new runtime behavior and failure modes. Do not report unexecuted checks as passing.

See `SECURITY.md` before adding integrations that execute tools or store user-provided content.
