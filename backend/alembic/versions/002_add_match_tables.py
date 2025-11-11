"""Add match tables - Likes, Matches, Messages, BlockedUsers

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 建立 likes 表
    op.create_table(
        'likes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('from_user_id != to_user_id', name='no_self_like'),
        sa.UniqueConstraint('from_user_id', 'to_user_id', name='unique_like')
    )

    # 建立 matches 表
    op.create_table(
        'matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user1_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user2_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('matched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('unmatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('unmatched_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user1_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user2_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['unmatched_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('user1_id < user2_id', name='user_order'),
        sa.UniqueConstraint('user1_id', 'user2_id', name='unique_match')
    )
    op.create_index(op.f('ix_matches_status'), 'matches', ['status'], unique=False)

    # 建立 messages 表
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('match_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=20), server_default='TEXT', nullable=True),
        sa.Column('is_read', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_match_id'), 'messages', ['match_id'], unique=False)
    op.create_index(op.f('ix_messages_sent_at'), 'messages', ['sent_at'], unique=False)

    # 建立 blocked_users 表
    op.create_table(
        'blocked_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blocker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blocked_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('blocker_id != blocked_id', name='no_self_block'),
        sa.UniqueConstraint('blocker_id', 'blocked_id', name='unique_block')
    )


def downgrade() -> None:
    op.drop_table('blocked_users')
    op.drop_index(op.f('ix_messages_sent_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_match_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_matches_status'), table_name='matches')
    op.drop_table('matches')
    op.drop_table('likes')
