# MergeMeet 開發指南

> **🎯 快速參考**: 本文件為快速啟動指南。詳細開發流程請使用 **Skill: mergemeet-quickstart**

---

## 📋 專案資訊

- **專案**: MergeMeet 交友平台
- **技術棧**: FastAPI + Vue 3 + PostgreSQL + PostGIS + Redis
- **階段**: MVP (Week 1-5)
- **測試覆蓋率**: >80%

---

## 🚀 快速啟動（3 步驟）

```bash
# 1. 啟動基礎服務
docker compose up -d

# 2. 啟動後端 (http://localhost:8000/docs)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 啟動前端 (http://localhost:5173)
cd frontend && npm run dev
```

---

## 🎓 Claude Code Skills 系統

### 核心 Skills

| Skill | 用途 | 觸發方式 |
|-------|------|----------|
| 🚨 **api-routing-standards** | API 路由規範（防止 404） | 編輯 API 路由時強制觸發 |
| 🔧 **backend-dev-fastapi** | FastAPI 後端開發指南 | 編輯後端程式碼時 |
| 🎨 **frontend-dev-vue3** | Vue 3 前端開發指南 | 編輯前端組件時 |
| 🗄️ **database-planning** | 資料庫設計標準 | 編輯資料模型時 |
| 🧪 **testing-guide** | 測試策略與 TDD | 編寫測試時 |
| 📊 **product-management** | 產品需求管理 | 規劃功能時 |
| 📚 **mergemeet-quickstart** | 完整開發流程指南 | 需要詳細指南時 |

### 手動使用

```bash
# 查看詳細開發流程
使用 Skill: mergemeet-quickstart

# 查看 API 路由規範
使用 Skill: api-routing-standards

# 查看後端開發指南
使用 Skill: backend-dev-fastapi
```

---

## 🚨 最重要的規則

**API URL 無尾隨斜線** - 所有端點不使用 `/` 結尾

```python
# ✅ 正確
@router.get("")                  # GET /api/profile
@router.put("/interests")        # PUT /api/profile/interests

# ❌ 錯誤（會導致 404）
@router.get("/")                 # ❌ 404
@router.put("/interests/")       # ❌ 404
```

```javascript
// 前端也必須無尾隨斜線
await axios.get('/api/profile')          // ✅
await axios.get('/api/profile/')         // ❌ 404
```

**詳細規範**: 使用 `Skill: api-routing-standards`

---

## 📂 專案結構

```
mergemeet/
├── backend/              # FastAPI (8 模組, 8 模型, 70+ 測試)
│   ├── app/api/         # API 路由
│   ├── app/models/      # SQLAlchemy 模型
│   └── tests/           # pytest 測試
├── frontend/            # Vue 3 (5 組件, 11 頁面, 7 stores)
│   └── src/
└── .claude/skills/      # Skills 配置
```

---

## 🔧 常用指令速查

```bash
# 資料庫
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet

# 測試
cd backend && pytest -v --cov=app

# 重置
docker compose down -v && docker compose up -d
```

**完整指令清單**: 使用 `Skill: mergemeet-quickstart`

---

## 📚 相關文件

- **README.md** - 專案總覽
- **ARCHITECTURE.md** - 技術架構
- **00_進度追蹤表.md** - 開發進度
- **Skill: mergemeet-quickstart** - 完整開發指南 ⭐

---

## 🎯 核心原則

1. 🚨 **API URL 無尾隨斜線** - 違反會導致 404
2. 🎓 **使用 Skills 系統** - 開發時參考指南
3. ⚡ **Async 優先** - 後端使用 async/await
4. 🧩 **Composition API** - 前端使用 `<script setup>`
5. 🧪 **測試驅動** - TDD 開發流程

---

**開發愉快！** 🚀

💡 **需要詳細指南？** 使用 `Skill: mergemeet-quickstart`
