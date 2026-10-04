"""session: enabled_submission_types

Revision ID: 0002_enabled_submission_types
Revises: 0001_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_enabled_submission_types"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "class_sessions",
        sa.Column(
            "enabled_submission_types",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("class_sessions", "enabled_submission_types")
