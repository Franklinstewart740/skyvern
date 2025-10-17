"""Add LLM benchmarking telemetry tables

Revision ID: a1b2c3d4e5f6
Revises: 74f6954344ee
Create Date: 2025-10-17 00:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "74f6954344ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create llm_call_telemetry table for detailed trace data
    op.create_table(
        "llm_call_telemetry",
        sa.Column("telemetry_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("llm_key", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("prompt_name", sa.String(), nullable=False),
        sa.Column("step_id", sa.String(), nullable=True),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("workflow_run_id", sa.String(), nullable=True),
        sa.Column("thought_id", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Numeric(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_type", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("telemetry_id"),
    )
    
    # Create indexes for common queries
    op.create_index(
        "ix_llm_call_telemetry_org_created",
        "llm_call_telemetry",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_llm_call_telemetry_provider_created",
        "llm_call_telemetry",
        ["provider", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_llm_call_telemetry_prompt_name",
        "llm_call_telemetry",
        ["prompt_name"],
        unique=False,
    )
    op.create_index(
        "ix_llm_call_telemetry_success",
        "llm_call_telemetry",
        ["success"],
        unique=False,
    )
    
    # Create llm_benchmark_summaries table for aggregated data
    op.create_table(
        "llm_benchmark_summaries",
        sa.Column("summary_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("prompt_name", sa.String(), nullable=True),
        sa.Column("time_period", sa.String(), nullable=False),  # hourly, daily
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("total_calls", sa.Integer(), nullable=False),
        sa.Column("successful_calls", sa.Integer(), nullable=False),
        sa.Column("failed_calls", sa.Integer(), nullable=False),
        sa.Column("avg_latency_ms", sa.FLOAT(), nullable=True),
        sa.Column("p50_latency_ms", sa.FLOAT(), nullable=True),
        sa.Column("p95_latency_ms", sa.FLOAT(), nullable=True),
        sa.Column("p99_latency_ms", sa.FLOAT(), nullable=True),
        sa.Column("total_input_tokens", sa.BigInteger(), nullable=True),
        sa.Column("total_output_tokens", sa.BigInteger(), nullable=True),
        sa.Column("total_reasoning_tokens", sa.BigInteger(), nullable=True),
        sa.Column("total_cached_tokens", sa.BigInteger(), nullable=True),
        sa.Column("total_cost", sa.Numeric(), nullable=True),
        sa.Column("avg_cost", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("summary_id"),
    )
    
    # Create indexes for aggregated queries
    op.create_index(
        "ix_llm_benchmark_summaries_provider_period",
        "llm_benchmark_summaries",
        ["provider", "period_start", "period_end"],
        unique=False,
    )
    op.create_index(
        "ix_llm_benchmark_summaries_org_period",
        "llm_benchmark_summaries",
        ["organization_id", "period_start"],
        unique=False,
    )
    op.create_index(
        "ix_llm_benchmark_summaries_time_period",
        "llm_benchmark_summaries",
        ["time_period", "period_start"],
        unique=False,
    )


def downgrade() -> None:
    # Drop llm_benchmark_summaries table and indexes
    op.drop_index("ix_llm_benchmark_summaries_time_period", table_name="llm_benchmark_summaries")
    op.drop_index("ix_llm_benchmark_summaries_org_period", table_name="llm_benchmark_summaries")
    op.drop_index("ix_llm_benchmark_summaries_provider_period", table_name="llm_benchmark_summaries")
    op.drop_table("llm_benchmark_summaries")
    
    # Drop llm_call_telemetry table and indexes
    op.drop_index("ix_llm_call_telemetry_success", table_name="llm_call_telemetry")
    op.drop_index("ix_llm_call_telemetry_prompt_name", table_name="llm_call_telemetry")
    op.drop_index("ix_llm_call_telemetry_provider_created", table_name="llm_call_telemetry")
    op.drop_index("ix_llm_call_telemetry_org_created", table_name="llm_call_telemetry")
    op.drop_table("llm_call_telemetry")
