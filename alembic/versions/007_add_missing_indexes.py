"""Add missing indexes for performance optimization

Revision ID: 007
Revises: 006
Create Date: 2024-11-16 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. blocked_users 表索引 - 優化封鎖列表查詢
    # 優化查詢如：SELECT * FROM blocked_users WHERE blocker_id = ?
    op.create_index(
        'ix_blocked_users_blocker_id',
        'blocked_users',
        ['blocker_id'],
        unique=False
    )

    # 優化反向查詢：檢查用戶是否被封鎖
    # 優化查詢如：SELECT * FROM blocked_users WHERE blocked_id = ?
    op.create_index(
        'ix_blocked_users_blocked_id',
        'blocked_users',
        ['blocked_id'],
        unique=False
    )

    # 2. moderation_logs 複合索引 - 優化審核日誌查詢
    # 優化查詢如：SELECT * FROM moderation_logs WHERE user_id = ? ORDER BY created_at DESC
    op.create_index(
        'ix_moderation_logs_user_created',
        'moderation_logs',
        ['user_id', 'created_at'],
        unique=False
    )

    # 3. sensitive_words 分類索引 - 優化敏感詞分類查詢
    # 優化查詢如：SELECT * FROM sensitive_words WHERE category = ? AND is_active = TRUE
    op.create_index(
        'ix_sensitive_words_category_active',
        'sensitive_words',
        ['category', 'is_active'],
        unique=False
    )

    # 4. matches 表狀態索引 - 優化單用戶配對查詢
    # 優化查詢如：SELECT * FROM matches WHERE user1_id = ? AND status = 'ACTIVE'
    op.create_index(
        'ix_matches_user1_status',
        'matches',
        ['user1_id', 'status'],
        unique=False
    )

    # 優化第二用戶的配對查詢
    # 優化查詢如：SELECT * FROM matches WHERE user2_id = ? AND status = 'ACTIVE'
    op.create_index(
        'ix_matches_user2_status',
        'matches',
        ['user2_id', 'status'],
        unique=False
    )

    # 5. messages 表三元組索引 - 優化未讀訊息過濾查詢
    # 優化查詢如：SELECT * FROM messages WHERE match_id = ? AND is_read IS NULL AND deleted_at IS NULL
    op.create_index(
        'ix_messages_match_read_deleted',
        'messages',
        ['match_id', 'is_read', 'deleted_at'],
        unique=False
    )


def downgrade() -> None:
    # 刪除索引（按創建順序的反向）
    op.drop_index('ix_messages_match_read_deleted', table_name='messages')
    op.drop_index('ix_matches_user2_status', table_name='matches')
    op.drop_index('ix_matches_user1_status', table_name='matches')
    op.drop_index('ix_sensitive_words_category_active', table_name='sensitive_words')
    op.drop_index('ix_moderation_logs_user_created', table_name='moderation_logs')
    op.drop_index('ix_blocked_users_blocked_id', table_name='blocked_users')
    op.drop_index('ix_blocked_users_blocker_id', table_name='blocked_users')
