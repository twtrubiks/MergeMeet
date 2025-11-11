#!/bin/bash
# 清理 Python 緩存並重新運行測試

echo "🧹 清理 Python 字節碼緩存..."

# 刪除所有 __pycache__ 目錄
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# 刪除所有 .pyc 文件
find . -name "*.pyc" -delete 2>/dev/null

# 刪除 .pytest_cache
rm -rf .pytest_cache

echo "✅ 緩存清理完成"
echo ""
echo "現在請執行測試："
echo "  pytest"
echo "  或"
echo "  pytest -v"
