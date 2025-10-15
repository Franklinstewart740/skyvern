"""Add prompt cache table for LLM caching and replay

Revision ID: 74f6954344ee
Revises: d648e2df239e
Create Date: 2025-10-15 23:39:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "74f6954344ee"
down_revision: Union[str, None] = "d648e2df239e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_cache",
        sa.Column("prompt_cache_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("prompt_hash", sa.String(), nullable=False),
        sa.Column("llm_key", sa.String(), nullable=False),
        sa.Column("model_config", sa.JSON(), nullable=True),
        sa.Column("prompt_text", sa.UnicodeText(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_cost", sa.Numeric(), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ttl_expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified_at", sa.DateTime(), nullable=False),
        sa.Column("accessed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("prompt_cache_id"),
    )
    op.create_index(
        "ix_prompt_cache_hash_llm_key",
        "prompt_cache",
        ["prompt_hash", "llm_key"],
        unique=False,
    )
    op.create_index(
        "ix_prompt_cache_org_created",
        "prompt_cache",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_prompt_cache_expires_at",
        "prompt_cache",
        ["ttl_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_prompt_cache_expires_at", table_name="prompt_cache")
    op.drop_index("ix_prompt_cache_org_created", table_name="prompt_cache")
    op.drop_index("ix_prompt_cache_hash_llm_key", table_name="prompt_cache")
    op.drop_table("prompt_cache")
