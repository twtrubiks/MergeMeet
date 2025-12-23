"""Alembic 環境配置"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# 加入專案路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 導入 Alembic Config 對象
config = context.config

# 解析 alembic.ini 的日誌設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 導入所有模型（這樣 Alembic 才能偵測到）
from app.core.database import Base
from app.models import (
    User, Profile, Photo, InterestTag, profile_interests,
    Like, Match, Message, BlockedUser
)
from app.models.report import Report  # 舉報模型

# 設定 MetaData
target_metadata = Base.metadata

# 從環境變數讀取資料庫 URL
from app.core.config import settings

# Alembic 需要使用同步驅動，將 asyncpg 替換為 psycopg2
sync_database_url = str(settings.DATABASE_URL).replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", sync_database_url)


def include_name(name, type_, parent_names):
    """
    在 schema 層級排除 PostGIS 相關的 schema

    這個函數在更早的階段過濾，避免 Alembic 去反射不需要的 schema。
    參考: https://alembic.sqlalchemy.org/en/latest/autogenerate.html

    Args:
        name: 對象名稱
        type_: 對象類型 (schema, table, column 等)
        parent_names: 父級名稱字典

    Returns:
        bool: True 表示包含此對象，False 表示排除
    """
    if type_ == "schema":
        # 只處理 public schema（None = 預設 schema）
        # 排除 tiger, tiger_data, topology 等 PostGIS 相關 schema
        return name in [None, "public"]
    return True


def include_object(object, name, type_, reflected, compare_to):
    """
    排除不需要追蹤的表和 schema

    Args:
        object: 資料庫對象
        name: 對象名稱
        type_: 對象類型 (table, column, index 等)
        reflected: 是否從資料庫反射而來
        compare_to: 比較目標

    Returns:
        bool: True 表示包含此對象，False 表示排除
    """
    # 排除 tiger 和 topology schema 的所有對象
    if hasattr(object, 'schema') and object.schema in ['tiger', 'topology', 'tiger_data']:
        return False

    # 排除 PostGIS 系統表
    postgis_tables = [
        'spatial_ref_sys', 'geography_columns', 'geometry_columns',
        'raster_columns', 'raster_overviews'
    ]
    if type_ == "table" and name in postgis_tables:
        return False

    # 對於從資料庫反射的表，只包含在我們的 metadata 中定義的表
    if type_ == "table" and reflected:
        return name in target_metadata.tables

    return True


def run_migrations_offline() -> None:
    """
    在 'offline' 模式下運行遷移

    這會配置 context 只使用 URL，而不需要建立 Engine
    適用於生成 SQL 腳本而不執行
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 比較欄位類型變更
        compare_server_default=True,  # 比較預設值變更
        include_name=include_name,  # 在 schema 層級排除 PostGIS
        include_object=include_object,  # 排除 PostGIS 表
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在 'online' 模式下運行遷移

    建立 Engine 並關聯 connection 到 context
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 比較欄位類型變更
            compare_server_default=True,  # 比較預設值變更
            include_name=include_name,  # 在 schema 層級排除 PostGIS
            include_object=include_object,  # 排除 PostGIS 表
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
