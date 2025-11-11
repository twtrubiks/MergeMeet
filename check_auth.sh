#!/bin/bash

echo "=== 檢查 MergeMeet 認證狀態 ==="
echo ""

# 檢查資料庫中的 is_active 狀態
echo "1. 檢查資料庫中所有用戶的 is_active 狀態："
docker exec -i mergemeet_postgres psql -U mergemeet -d mergemeet -c "SELECT email, is_active, email_verified, created_at FROM users ORDER BY created_at DESC LIMIT 5;" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "   ⚠️  無法連接到資料庫。請確認 Docker 容器正在運行。"
    echo ""
    echo "   嘗試啟動資料庫："
    echo "   docker compose up -d"
fi

echo ""
echo "2. 檢查後端伺服器狀態："
curl -s http://localhost:8000/api/hello > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ 後端伺服器運行正常 (http://localhost:8000)"
else
    echo "   ❌ 後端伺服器未運行"
    echo "   啟動後端："
    echo "   cd mergemeet/backend && uvicorn app.main:app --reload"
fi

echo ""
echo "3. 檢查前端伺服器狀態："
curl -s http://localhost:5173 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ 前端伺服器運行正常 (http://localhost:5173)"
else
    echo "   ❌ 前端伺服器未運行"
    echo "   啟動前端："
    echo "   cd mergemeet/frontend && npm run dev"
fi

echo ""
echo "=== 修復建議 ==="
echo ""
echo "如果仍然遇到 403 錯誤："
echo "1. 執行資料庫修復："
echo "   docker exec -i mergemeet_postgres psql -U mergemeet -d mergemeet -c \"UPDATE users SET is_active = TRUE WHERE is_active IS NULL;\""
echo ""
echo "2. 清除瀏覽器 localStorage："
echo "   在瀏覽器 Console 中執行："
echo "   localStorage.clear(); location.reload();"
echo ""
echo "3. 重新登入或註冊新帳號"
echo ""
