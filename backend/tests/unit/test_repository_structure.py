"""
Minimal smoke test — verifies the repository structure is sane
before any backend packages are installed.

These tests run in CI immediately and can expand significantly in Task 2.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent


def test_env_example_exists() -> None:
    """Ensure .env.example exists and contains required keys."""
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists(), ".env.example must exist"
    content = env_example.read_text(encoding="utf-8")
    required_keys = [
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
        "DEFAULT_MODEL_PROVIDER",
        "PAYLOAD_LOG_LEVEL",
    ]
    for key in required_keys:
        assert key in content, f"{key} missing from .env.example"


def test_env_example_no_real_secrets() -> None:
    """Ensure .env.example does not contain real credentials."""
    env_example = REPO_ROOT / ".env.example"
    content = env_example.read_text(encoding="utf-8")
    # These patterns would indicate a real key was accidentally committed
    forbidden_patterns = [
        "sk-",      # OpenAI key prefix
        "AIza",     # Google API key prefix
    ]
    for pattern in forbidden_patterns:
        assert pattern not in content, f"Possible real API key pattern '{pattern}' found in .env.example"


def test_gitignore_excludes_env() -> None:
    """Ensure .gitignore excludes .env files."""
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore must exist"
    content = gitignore.read_text(encoding="utf-8")
    assert ".env" in content
    assert "venv/" in content
    assert "node_modules/" in content


def test_docker_compose_exists() -> None:
    """Ensure docker-compose.yml exists with required services."""
    compose = REPO_ROOT / "docker-compose.yml"
    assert compose.exists(), "docker-compose.yml must exist"
    content = compose.read_text(encoding="utf-8")
    required_services = ["postgres", "redis", "backend", "frontend", "prometheus", "grafana"]
    for svc in required_services:
        assert svc in content, f"Service '{svc}' missing from docker-compose.yml"


def test_pyproject_toml_exists() -> None:
    """Ensure backend pyproject.toml exists with required packages."""
    pyproject = REPO_ROOT / "backend" / "pyproject.toml"
    assert pyproject.exists(), "backend/pyproject.toml must exist"
    content = pyproject.read_text(encoding="utf-8")
    required_packages = ["fastapi", "sqlalchemy", "alembic", "pydantic", "redis"]
    for pkg in required_packages:
        assert pkg in content, f"Package '{pkg}' missing from pyproject.toml"


def test_ci_workflow_exists() -> None:
    """Ensure GitHub Actions CI workflow exists."""
    ci = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci.exists(), ".github/workflows/ci.yml must exist"
    content = ci.read_text(encoding="utf-8")
    assert "pytest" in content
    assert "ruff" in content
    assert "npm" in content


def test_directory_structure() -> None:
    """Ensure all required directories exist."""
    required_dirs = [
        "backend/app/api/v1/endpoints",
        "backend/app/core",
        "backend/app/models",
        "backend/app/schemas",
        "backend/app/services",
        "backend/app/tools",
        "backend/app/evaluation",
        "backend/app/providers",
        "backend/app/observability",
        "backend/alembic/versions",
        "backend/tests/unit",
        "backend/tests/integration",
        "frontend/src/components",
        "frontend/src/pages",
        "frontend/src/hooks",
        "frontend/src/services",
        "frontend/src/types",
        "deployment/docker",
        "deployment/grafana/dashboards",
        "deployment/prometheus",
        "scripts",
        "docs/diagrams",
        ".github/workflows",
    ]
    for d in required_dirs:
        path = REPO_ROOT / d
        assert path.exists() and path.is_dir(), f"Directory '{d}' must exist"


def test_no_env_file_committed() -> None:
    """Ensure .env file is not present (should never be committed)."""
    env_file = REPO_ROOT / ".env"
    assert not env_file.exists(), (
        ".env file must NOT be committed to the repository. "
        "Use .env.example with placeholder values only."
    )
