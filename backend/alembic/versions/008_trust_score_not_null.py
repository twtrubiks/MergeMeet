"""trust_score 加入 NOT NULL 約束

Revision ID: 008
Revises: d793da79649c
Create Date: 2026-03-15
"""

import sqlalchemy as sa

from alembic import op

revision = "008"
down_revision = "d793da79649c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 先將現有 NULL 值填為預設值 50
    op.execute("UPDATE users SET trust_score = 50 WHERE trust_score IS NULL")
    # 加入 NOT NULL 約束與 server default
    op.alter_column(
        "users",
        "trust_score",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="50",
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "trust_score",
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
