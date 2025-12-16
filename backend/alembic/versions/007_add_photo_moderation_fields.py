"""add photo moderation fields

Revision ID: 007_photo_moderation
Revises: e44e390409f1
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_photo_moderation'
down_revision = 'e44e390409f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增照片審核欄位"""
    # 新增 moderation_status 欄位（現有照片預設為 APPROVED）
    op.add_column('photos', sa.Column(
        'moderation_status',
        sa.String(length=20),
        nullable=False,
        server_default='APPROVED'
    ))

    # 新增拒絕原因欄位
    op.add_column('photos', sa.Column(
        'rejection_reason',
        sa.Text(),
        nullable=True
    ))

    # 新增審核者欄位
    op.add_column('photos', sa.Column(
        'reviewed_by',
        postgresql.UUID(as_uuid=True),
        nullable=True
    ))

    # 新增審核時間欄位
    op.add_column('photos', sa.Column(
        'reviewed_at',
        sa.DateTime(timezone=True),
        nullable=True
    ))

    # 新增自動審核分數欄位（預留擴展）
    op.add_column('photos', sa.Column(
        'auto_moderation_score',
        sa.Integer(),
        nullable=True
    ))

    # 新增自動審核標籤欄位（預留擴展）
    op.add_column('photos', sa.Column(
        'auto_moderation_labels',
        sa.Text(),
        nullable=True
    ))

    # 建立 moderation_status 索引
    op.create_index(
        'ix_photos_moderation_status',
        'photos',
        ['moderation_status']
    )

    # 建立外鍵約束
    op.create_foreign_key(
        'fk_photos_reviewed_by',
        'photos', 'users',
        ['reviewed_by'], ['id'],
        ondelete='SET NULL'
    )

    # 將現有照片標記為已審核，並設定審核時間為建立時間
    op.execute("""
        UPDATE photos
        SET moderation_status = 'APPROVED',
            reviewed_at = created_at
        WHERE moderation_status = 'APPROVED'
    """)

    # 移除預設值，讓新上傳的照片使用模型定義的預設值 PENDING
    op.alter_column('photos', 'moderation_status', server_default=None)


def downgrade() -> None:
    """移除照片審核欄位"""
    # 移除外鍵約束
    op.drop_constraint('fk_photos_reviewed_by', 'photos', type_='foreignkey')

    # 移除索引
    op.drop_index('ix_photos_moderation_status', table_name='photos')

    # 移除欄位
    op.drop_column('photos', 'auto_moderation_labels')
    op.drop_column('photos', 'auto_moderation_score')
    op.drop_column('photos', 'reviewed_at')
    op.drop_column('photos', 'reviewed_by')
    op.drop_column('photos', 'rejection_reason')
    op.drop_column('photos', 'moderation_status')
