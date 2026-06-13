"""users 加入 deleted_at 軟刪除欄位

刪除帳號功能：用戶請求刪除時標記 deleted_at（30 天寬限期），
到期後由背景清理任務真正刪除。索引供清理任務掃描使用。

Revision ID: 010
Revises: 009
Create Date: 2026-06-12
"""

import sqlalchemy as sa

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_column("users", "deleted_at")
