"""Initial schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-25 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── tasks ────────────────────────────────────────────────────────────────
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('request_id', sa.String(length=255), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('model_provider', sa.String(length=100), nullable=False, server_default='mock'),
        sa.Column('tool_ids', sa.JSON(), nullable=False),
        sa.Column('input_payload', sa.JSON(), nullable=True),
        sa.Column('output_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('token_usage_input', sa.Integer(), nullable=True),
        sa.Column('token_usage_output', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
    )
    op.create_index('ix_tasks_id', 'tasks', ['id'])
    op.create_index('ix_tasks_request_id', 'tasks', ['request_id'])
    op.create_index('ix_tasks_idempotency_key', 'tasks', ['idempotency_key'], unique=True)
    op.create_index('ix_tasks_status', 'tasks', ['status'])

    # ─── execution_steps ──────────────────────────────────────────────────────
    op.create_table(
        'execution_steps',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('task_id', sa.String(length=36), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('input', sa.JSON(), nullable=True),
        sa.Column('output', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
    )
    op.create_index('ix_execution_steps_task_id', 'execution_steps', ['task_id'])

    # ─── tools ────────────────────────────────────────────────────────────────
    op.create_table(
        'tools',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('version', sa.String(length=50), nullable=False, server_default='1.0.0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('input_schema', sa.JSON(), nullable=False),
        sa.Column('output_schema', sa.JSON(), nullable=False),
        sa.Column('permission_level', sa.String(length=50), nullable=False, server_default='PUBLIC'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_tools_name', 'tools', ['name'], unique=True)

    # ─── evaluation_datasets ──────────────────────────────────────────────────
    op.create_table(
        'evaluation_datasets',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_evaluation_datasets_name', 'evaluation_datasets', ['name'], unique=True)

    # ─── evaluation_cases ─────────────────────────────────────────────────────
    op.create_table(
        'evaluation_cases',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('dataset_id', sa.String(length=36), sa.ForeignKey('evaluation_datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('input', sa.JSON(), nullable=False),
        sa.Column('expected_output', sa.JSON(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_evaluation_cases_dataset_id', 'evaluation_cases', ['dataset_id'])

    # ─── evaluation_runs ──────────────────────────────────────────────────────
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('dataset_id', sa.String(length=36), sa.ForeignKey('evaluation_datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('runtime_version', sa.String(length=100), nullable=False, server_default='0.1.0'),
        sa.Column('model_provider', sa.String(length=100), nullable=False, server_default='mock'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_evaluation_runs_dataset_id', 'evaluation_runs', ['dataset_id'])
    op.create_index('ix_evaluation_runs_status', 'evaluation_runs', ['status'])

    # ─── evaluation_results ───────────────────────────────────────────────────
    op.create_table(
        'evaluation_results',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('run_id', sa.String(length=36), sa.ForeignKey('evaluation_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('evaluation_cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actual_output', sa.JSON(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('assertions', sa.JSON(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
    )
    op.create_index('ix_evaluation_results_run_id', 'evaluation_results', ['run_id'])
    op.create_index('ix_evaluation_results_case_id', 'evaluation_results', ['case_id'])


def downgrade() -> None:
    op.drop_table('evaluation_results')
    op.drop_table('evaluation_runs')
    op.drop_table('evaluation_cases')
    op.drop_table('evaluation_datasets')
    op.drop_table('tools')
    op.drop_table('execution_steps')
    op.drop_table('tasks')
