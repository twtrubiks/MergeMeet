#!/bin/bash
# MergeMeet 狀態檢查腳本

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 檢查 MergeMeet 服務狀態...${NC}"
echo ""

# 檢查 Docker 服務
echo -e "${BLUE}📦 Docker 服務:${NC}"
if docker-compose ps | grep -q "mergemeet_postgres.*Up"; then
    echo -e "${GREEN}✅ PostgreSQL 運行中${NC}"
else
    echo -e "${RED}❌ PostgreSQL 未運行${NC}"
fi

if docker-compose ps | grep -q "mergemeet_redis.*Up"; then
    echo -e "${GREEN}✅ Redis 運行中${NC}"
else
    echo -e "${RED}❌ Redis 未運行${NC}"
fi

echo ""

# 檢查後端
echo -e "${BLUE}🐍 後端 API:${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 後端 API 運行中 (http://localhost:8000)${NC}"
else
    echo -e "${RED}❌ 後端 API 未運行${NC}"
fi

echo ""

# 檢查前端
echo -e "${BLUE}🎨 前端:${NC}"
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 前端運行中 (http://localhost:5173)${NC}"
else
    echo -e "${RED}❌ 前端未運行${NC}"
fi

echo ""
echo -e "${BLUE}完成檢查${NC}"
