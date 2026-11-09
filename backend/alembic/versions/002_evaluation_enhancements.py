"""evaluation enhancements — Task 3

Revision ID: 002
Revises: 001
Create Date: 2026-10-26

Adds:
  evaluation_cases  — name, assertion_type, timeout_ms, expect_error
  evaluation_runs   — total_cases, passed_cases, failed_cases, errored_cases,
                      timed_out_cases, pass_rate, error_rate, timeout_rate,
                      latency_p50_ms, latency_p95_ms, latency_p99_ms
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "002"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── evaluation_cases ──────────────────────────────────────────────────────
    with op.batch_alter_table("evaluation_cases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(255), nullable=True))
        batch_op.add_column(
            sa.Column("assertion_type", sa.String(50), nullable=False, server_default="exact")
        )
        batch_op.add_column(sa.Column("timeout_ms", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("expect_error", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    # ── evaluation_runs ───────────────────────────────────────────────────────
    with op.batch_alter_table("evaluation_runs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("total_cases", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("passed_cases", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("failed_cases", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("errored_cases", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("timed_out_cases", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("pass_rate", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("error_rate", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("timeout_rate", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("latency_p50_ms", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("latency_p95_ms", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("latency_p99_ms", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("evaluation_runs", schema=None) as batch_op:
        for col in (
            "latency_p99_ms", "latency_p95_ms", "latency_p50_ms",
            "timeout_rate", "error_rate", "pass_rate",
            "timed_out_cases", "errored_cases", "failed_cases",
            "passed_cases", "total_cases",
        ):
            batch_op.drop_column(col)

    with op.batch_alter_table("evaluation_cases", schema=None) as batch_op:
        for col in ("expect_error", "timeout_ms", "assertion_type", "name"):
            batch_op.drop_column(col)
