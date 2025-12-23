"""add_reports_table

Revision ID: d793da79649c
Revises: 007_photo_moderation
Create Date: 2025-12-23 15:48:19.030797

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd793da79649c'
down_revision = '007_photo_moderation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 建立 reports 表
    op.create_table('reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('reporter_id', sa.UUID(), nullable=False),
        sa.Column('reported_user_id', sa.UUID(), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('reporter_id != reported_user_id', name='no_self_report'),
        sa.ForeignKeyConstraint(['reported_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    # 建立索引
    op.create_index('ix_reports_reported_user_id', 'reports', ['reported_user_id'], unique=False)
    op.create_index('ix_reports_reporter_id', 'reports', ['reporter_id'], unique=False)
    op.create_index('ix_reports_status', 'reports', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_reports_status', table_name='reports')
    op.drop_index('ix_reports_reporter_id', table_name='reports')
    op.drop_index('ix_reports_reported_user_id', table_name='reports')
    op.drop_table('reports')
