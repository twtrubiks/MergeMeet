"""新增 trust_score_logs 審計表

信任分數變更歷史：每次 trust_score 調整時同交易寫入日誌，
供用戶爭議追溯與管理員審計（複合索引依用戶查詢歷史）。

Revision ID: 011
Revises: 010
Create Date: 2026-06-13
"""

import sqlalchemy as sa

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trust_score_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("adjustment", sa.Integer(), nullable=False),
        sa.Column("new_score", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_trust_score_logs_user_created", "trust_score_logs", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_trust_score_logs_user_created", table_name="trust_score_logs")
    op.drop_table("trust_score_logs")
