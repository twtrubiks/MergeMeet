#!/bin/bash
# MergeMeet 開發伺服器啟動腳本

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 啟動 MergeMeet 開發環境...${NC}"

cd "$(dirname "$0")/.."

# 檢查 Docker 服務
echo -e "${BLUE}📦 檢查資料庫服務...${NC}"
docker-compose ps | grep -q "mergemeet_postgres.*Up" || {
    echo "啟動 PostgreSQL 和 Redis..."
    docker-compose up -d postgres redis
    sleep 3
}
echo -e "${GREEN}✅ 資料庫服務運行中${NC}"

# 啟動後端
echo -e "${BLUE}🐍 啟動後端 API (Port 8000)...${NC}"
cd backend
source venv/bin/activate

# 背景執行後端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}✅ 後端已啟動 (PID: $BACKEND_PID)${NC}"

cd ..

# 啟動前端
echo -e "${BLUE}🎨 啟動前端 (Port 5173)...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✅ 前端已啟動 (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}✨ 開發環境已啟動！${NC}"
echo ""
echo "服務地址："
echo "  前端: http://localhost:5173"
echo "  後端 API: http://localhost:8000"
echo "  API 文檔: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服務"

# 等待中斷信號
trap "echo ''; echo '停止服務...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# 保持腳本運行
wait
