#!/bin/bash
# 初始化測試資料庫

set -e

echo "正在創建測試資料庫..."

# 使用 psql 創建測試資料庫
PGPASSWORD=YOUR_DB_PASSWORD_HERE psql -h localhost -U mergemeet -d postgres -c "DROP DATABASE IF EXISTS mergemeet_test;"
PGPASSWORD=YOUR_DB_PASSWORD_HERE psql -h localhost -U mergemeet -d postgres -c "CREATE DATABASE mergemeet_test;"
PGPASSWORD=YOUR_DB_PASSWORD_HERE psql -h localhost -U mergemeet -d mergemeet_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"

echo "✅ 測試資料庫 mergemeet_test 已創建（包含 PostGIS 擴展）"
