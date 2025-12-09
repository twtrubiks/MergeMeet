"""add_pass_table_for_skip_functionality

新增 passes 表記錄跳過操作，24 小時內跳過的用戶不會再次出現。
類似 Tinder 做法，24 小時後可重新配對，給用戶第二次機會。

Revision ID: 10bf13f37414
Revises: 006
Create Date: 2025-12-09 15:38:48.554461

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '10bf13f37414'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 創建 passes 表
    op.create_table(
        'passes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('from_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('passed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # 外鍵
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ondelete='CASCADE'),

        # 約束
        sa.CheckConstraint('from_user_id != to_user_id', name='no_self_pass'),
        sa.UniqueConstraint('from_user_id', 'to_user_id', name='unique_pass'),
    )

    # 創建索引（優化查詢效能）
    op.create_index('ix_passes_from_user_passed_at', 'passes', ['from_user_id', 'passed_at'])


def downgrade() -> None:
    # 刪除索引
    op.drop_index('ix_passes_from_user_passed_at', 'passes')

    # 刪除表
    op.drop_table('passes')
