"""Fix user schema - Add ban_reason and banned_until fields

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加缺少的 ban_reason 和 banned_until 欄位
    op.add_column('users', sa.Column('ban_reason', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('banned_until', sa.DateTime(timezone=True), nullable=True))

    # 如果 email_verification_token 欄位存在但 model 中沒有，則移除它
    # （暫時註解掉，因為可能還在使用）
    # op.drop_column('users', 'email_verification_token')


def downgrade() -> None:
    # 移除添加的欄位
    op.drop_column('users', 'banned_until')
    op.drop_column('users', 'ban_reason')

    # 如果需要，恢復 email_verification_token 欄位
    # op.add_column('users', sa.Column('email_verification_token', sa.String(length=255), nullable=True))
