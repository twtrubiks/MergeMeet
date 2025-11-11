#!/bin/bash
# MergeMeet 測試執行腳本

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 執行 MergeMeet 測試...${NC}"

cd "$(dirname "$0")/.."

# 後端測試
echo -e "${BLUE}🐍 執行後端測試...${NC}"
cd backend
source venv/bin/activate
pytest -v --cov=app --cov-report=term-missing
echo -e "${GREEN}✅ 後端測試完成${NC}"

cd ..

# 前端測試（未來實作）
echo -e "${BLUE}🎨 前端測試（待實作）...${NC}"
# cd frontend
# npm run test

echo ""
echo -e "${GREEN}✨ 所有測試完成！${NC}"
