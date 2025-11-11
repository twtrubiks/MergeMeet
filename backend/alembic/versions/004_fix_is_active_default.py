"""Fix is_active default value

Revision ID: 004
Revises: 003
Create Date: 2024-01-15 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 將所有現有用戶的 is_active 設為 True（如果是 NULL）
    op.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")

    # 2. 設置 is_active 欄位的預設值為 TRUE
    op.alter_column('users', 'is_active',
                    existing_type=sa.Boolean(),
                    server_default=sa.text('true'),
                    nullable=False)

    # 3. 同樣處理 email_verified 欄位（如果需要）
    op.execute("UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL")
    op.alter_column('users', 'email_verified',
                    existing_type=sa.Boolean(),
                    server_default=sa.text('false'),
                    nullable=False)

    # 4. 處理其他布林欄位
    op.execute("UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL")
    op.alter_column('users', 'is_admin',
                    existing_type=sa.Boolean(),
                    server_default=sa.text('false'),
                    nullable=False)


def downgrade() -> None:
    # 移除預設值
    op.alter_column('users', 'is_admin',
                    existing_type=sa.Boolean(),
                    server_default=None,
                    nullable=True)

    op.alter_column('users', 'email_verified',
                    existing_type=sa.Boolean(),
                    server_default=None,
                    nullable=True)

    op.alter_column('users', 'is_active',
                    existing_type=sa.Boolean(),
                    server_default=None,
                    nullable=True)
