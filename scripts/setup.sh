#!/bin/bash
# MergeMeet 環境設置腳本

set -e

echo "🚀 開始設置 MergeMeet 開發環境..."

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 檢查 Docker
echo -e "${BLUE}📦 檢查 Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安裝，請先安裝 Docker"
    exit 1
fi
echo -e "${GREEN}✅ Docker 已安裝${NC}"

# 檢查 Python
echo -e "${BLUE}🐍 檢查 Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 未安裝"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION 已安裝${NC}"

# 檢查 Node.js
echo -e "${BLUE}📗 檢查 Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安裝"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js $NODE_VERSION 已安裝${NC}"

# 啟動 Docker Compose
echo -e "${BLUE}🐳 啟動 PostgreSQL 和 Redis...${NC}"
cd "$(dirname "$0")/.."
docker-compose up -d postgres redis
echo -e "${GREEN}✅ 資料庫服務已啟動${NC}"

# 等待資料庫啟動
echo -e "${BLUE}⏳ 等待資料庫啟動...${NC}"
sleep 5

# 設置後端
echo -e "${BLUE}🔧 設置後端環境...${NC}"
cd backend

# 建立虛擬環境
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Python 虛擬環境已建立${NC}"
fi

# 啟動虛擬環境並安裝依賴
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-test.txt
echo -e "${GREEN}✅ Python 依賴已安裝${NC}"

# 複製環境變數檔案
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ .env 檔案已建立${NC}"
fi

cd ..

# 設置前端
echo -e "${BLUE}🎨 設置前端環境...${NC}"
cd frontend

# 安裝 npm 依賴
if [ ! -d "node_modules" ]; then
    npm install
    echo -e "${GREEN}✅ Node.js 依賴已安裝${NC}"
else
    echo -e "${GREEN}✅ Node.js 依賴已存在${NC}"
fi

cd ..

echo ""
echo -e "${GREEN}✨ 環境設置完成！${NC}"
echo ""
echo "下一步："
echo "  1. 執行 ./scripts/dev.sh 啟動開發伺服器"
echo "  2. 訪問 http://localhost:5173 查看前端"
echo "  3. 訪問 http://localhost:8000/docs 查看 API 文檔"
