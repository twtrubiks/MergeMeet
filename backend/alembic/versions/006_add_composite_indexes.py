"""Add composite indexes for performance optimization

Revision ID: 006
Revises: 005
Create Date: 2024-01-21 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 matches 表的複合索引：用於快速查詢用戶的所有配對
    # 優化查詢如：SELECT * FROM matches WHERE (user1_id = ? OR user2_id = ?) AND status = 'ACTIVE'
    op.create_index(
        'ix_matches_user1_user2_status',
        'matches',
        ['user1_id', 'user2_id', 'status'],
        unique=False
    )

    # 添加 messages 表的複合索引：用於快速查詢配對的訊息歷史（按時間排序）
    # 優化查詢如：SELECT * FROM messages WHERE match_id = ? ORDER BY sent_at DESC
    op.create_index(
        'ix_messages_match_sent',
        'messages',
        ['match_id', 'sent_at'],
        unique=False
    )

    # 添加 likes 表的複合索引：用於快速檢查雙向喜歡
    # 優化查詢如：SELECT * FROM likes WHERE from_user_id = ? AND to_user_id = ?
    op.create_index(
        'ix_likes_from_to',
        'likes',
        ['from_user_id', 'to_user_id'],
        unique=True  # 一個用戶只能喜歡另一個用戶一次
    )

    # 添加 messages 表的複合索引：用於快速計算未讀訊息數
    # 優化查詢如：SELECT COUNT(*) FROM messages WHERE match_id = ? AND sender_id = ? AND is_read IS NULL
    op.create_index(
        'ix_messages_match_sender_read',
        'messages',
        ['match_id', 'sender_id', 'is_read'],
        unique=False
    )


def downgrade() -> None:
    # 刪除索引（按創建順序的反向）
    op.drop_index('ix_messages_match_sender_read', table_name='messages')
    op.drop_index('ix_likes_from_to', table_name='likes')
    op.drop_index('ix_messages_match_sent', table_name='messages')
    op.drop_index('ix_matches_user1_user2_status', table_name='matches')
