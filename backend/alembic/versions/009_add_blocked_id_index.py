"""blocked_users.blocked_id 加入索引

探索頁排除「誰封鎖了我」的子查詢需要此索引，
UniqueConstraint(blocker_id, blocked_id) 的複合索引無法覆蓋 blocked_id 單獨查詢。

Revision ID: 009
Revises: 008
Create Date: 2026-03-15
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_blocked_users_blocked_id", "blocked_users", ["blocked_id"])


def downgrade() -> None:
    op.drop_index("ix_blocked_users_blocked_id", table_name="blocked_users")
