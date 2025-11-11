"""Initial schema - Users, Profiles, Photos, InterestTags

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 建立 users 表
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=True),
        sa.Column('email_verification_token', sa.String(length=255), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('trust_score', sa.Integer(), nullable=True),
        sa.Column('warning_count', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 建立 profiles 表
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, from_text='ST_GeogFromText', name='geography'), nullable=True),
        sa.Column('location_name', sa.String(length=255), nullable=True),
        sa.Column('min_age_preference', sa.Integer(), nullable=True),
        sa.Column('max_age_preference', sa.Integer(), nullable=True),
        sa.Column('max_distance_km', sa.Integer(), nullable=True),
        sa.Column('gender_preference', sa.String(length=20), nullable=True),
        sa.Column('is_complete', sa.Boolean(), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=True),
        sa.Column('last_active', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_profiles_user_id'), 'profiles', ['user_id'], unique=False)

    # 建立 interest_tags 表
    op.create_table(
        'interest_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('icon', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_interest_tags_category'), 'interest_tags', ['category'], unique=False)
    op.create_index(op.f('ix_interest_tags_name'), 'interest_tags', ['name'], unique=False)

    # 建立 photos 表
    op.create_table(
        'photos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.Column('is_profile_picture', sa.Boolean(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_photos_profile_id'), 'photos', ['profile_id'], unique=False)

    # 建立 profile_interests 關聯表
    op.create_table(
        'profile_interests',
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interest_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['interest_id'], ['interest_tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('profile_id', 'interest_id')
    )


def downgrade() -> None:
    op.drop_table('profile_interests')
    op.drop_index(op.f('ix_photos_profile_id'), table_name='photos')
    op.drop_table('photos')
    op.drop_index(op.f('ix_interest_tags_name'), table_name='interest_tags')
    op.drop_index(op.f('ix_interest_tags_category'), table_name='interest_tags')
    op.drop_table('interest_tags')
    op.drop_index(op.f('ix_profiles_user_id'), table_name='profiles')
    op.drop_table('profiles')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
