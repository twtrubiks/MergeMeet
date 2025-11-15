"""Add content moderation tables - SensitiveWords, ContentAppeals, ModerationLogs

Revision ID: 005
Revises: 004
Create Date: 2024-01-20 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 建立 sensitive_words 表
    op.create_table(
        'sensitive_words',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('action', sa.String(length=20), nullable=False, server_default='WARN'),
        sa.Column('is_regex', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('word', name='unique_sensitive_word')
    )
    op.create_index(op.f('ix_sensitive_words_word'), 'sensitive_words', ['word'], unique=True)
    op.create_index(op.f('ix_sensitive_words_is_active'), 'sensitive_words', ['is_active'], unique=False)

    # 建立 content_appeals 表
    op.create_table(
        'content_appeals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appeal_type', sa.String(length=50), nullable=False),
        sa.Column('rejected_content', sa.Text(), nullable=False),
        sa.Column('violations', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=True),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_appeals_user_id'), 'content_appeals', ['user_id'], unique=False)
    op.create_index(op.f('ix_content_appeals_status'), 'content_appeals', ['status'], unique=False)

    # 建立 moderation_logs 表
    op.create_table(
        'moderation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('original_content', sa.Text(), nullable=False),
        sa.Column('is_approved', sa.Boolean(), nullable=False),
        sa.Column('violations', sa.Text(), nullable=True),
        sa.Column('triggered_word_ids', sa.Text(), nullable=True),
        sa.Column('action_taken', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_moderation_logs_user_id'), 'moderation_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_moderation_logs_created_at'), 'moderation_logs', ['created_at'], unique=False)

    # 插入現有的敏感詞（從硬編碼遷移到資料庫）
    # 注意：這裡使用 UUID 需要生成函數，簡化起見先用 SQL 函數
    op.execute("""
        INSERT INTO sensitive_words (id, word, category, severity, action, is_regex, is_active, created_at)
        VALUES
            -- 色情相關
            (gen_random_uuid(), '色情', 'SEXUAL', 'HIGH', 'REJECT', false, true, now()),
            (gen_random_uuid(), '裸露', 'SEXUAL', 'HIGH', 'REJECT', false, true, now()),
            (gen_random_uuid(), '成人', 'SEXUAL', 'MEDIUM', 'WARN', false, true, now()),
            (gen_random_uuid(), '18禁', 'SEXUAL', 'HIGH', 'REJECT', false, true, now()),
            -- 詐騙相關
            (gen_random_uuid(), '詐騙', 'SCAM', 'HIGH', 'REJECT', false, true, now()),
            (gen_random_uuid(), '匯款', 'SCAM', 'MEDIUM', 'WARN', false, true, now()),
            (gen_random_uuid(), '轉帳', 'SCAM', 'MEDIUM', 'WARN', false, true, now()),
            (gen_random_uuid(), '投資', 'SCAM', 'LOW', 'WARN', false, true, now()),
            (gen_random_uuid(), '賺錢', 'SCAM', 'MEDIUM', 'WARN', false, true, now()),
            (gen_random_uuid(), '兼職', 'SCAM', 'LOW', 'WARN', false, true, now()),
            (gen_random_uuid(), '加賴', 'SCAM', 'MEDIUM', 'WARN', false, true, now()),
            -- 騷擾相關
            (gen_random_uuid(), '約炮', 'HARASSMENT', 'HIGH', 'REJECT', false, true, now()),
            (gen_random_uuid(), '一夜情', 'HARASSMENT', 'HIGH', 'REJECT', false, true, now()),
            (gen_random_uuid(), '援交', 'HARASSMENT', 'CRITICAL', 'AUTO_BAN', false, true, now()),
            -- 個人資訊
            (gen_random_uuid(), '身分證', 'PERSONAL_INFO', 'MEDIUM', 'WARN', false, true, now()),
            (gen_random_uuid(), '信用卡', 'PERSONAL_INFO', 'HIGH', 'REJECT', false, true, now()),
            (gen_random_uuid(), '銀行帳號', 'PERSONAL_INFO', 'HIGH', 'REJECT', false, true, now()),
            -- 暴力相關
            (gen_random_uuid(), '殺', 'VIOLENCE', 'MEDIUM', 'WARN', false, true, now()),
            (gen_random_uuid(), '死', 'VIOLENCE', 'LOW', 'WARN', false, true, now()),
            (gen_random_uuid(), '暴力', 'VIOLENCE', 'MEDIUM', 'WARN', false, true, now())
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_moderation_logs_created_at'), table_name='moderation_logs')
    op.drop_index(op.f('ix_moderation_logs_user_id'), table_name='moderation_logs')
    op.drop_table('moderation_logs')

    op.drop_index(op.f('ix_content_appeals_status'), table_name='content_appeals')
    op.drop_index(op.f('ix_content_appeals_user_id'), table_name='content_appeals')
    op.drop_table('content_appeals')

    op.drop_index(op.f('ix_sensitive_words_is_active'), table_name='sensitive_words')
    op.drop_index(op.f('ix_sensitive_words_word'), table_name='sensitive_words')
    op.drop_table('sensitive_words')
