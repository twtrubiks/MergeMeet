"""add_password_reset_fields_to_user

Revision ID: 5608b84f3973
Revises: 10bf13f37414
Create Date: 2025-12-12 15:44:47.391544

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5608b84f3973'
down_revision = '10bf13f37414'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加密碼重置欄位
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_users_password_reset_token'), 'users', ['password_reset_token'], unique=False)


def downgrade() -> None:
    # 移除密碼重置欄位
    op.drop_index(op.f('ix_users_password_reset_token'), table_name='users')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
