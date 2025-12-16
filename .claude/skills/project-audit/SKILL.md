---
name: project-audit
description: MergeMeet 專案健康度審查 Skill。全面檢查交友軟體核心功能完整性、前後端功能對應、潛在 Bug、流程合理性。當需要評估專案狀態或準備新功能開發時使用。
---

# 專案健康度審查 (Project Audit)

## 目的

全面檢查 MergeMeet 交友平台的健康狀態，確保：
1. **功能完整性** - 交友軟體核心功能是否齊全
2. **前後端一致性** - 後端 API 是否有對應的前端實現
3. **Bug 檢測** - 發現潛在問題和錯誤
4. **流程合理性** - 用戶體驗流程是否順暢

---

## 何時使用此 Skill

**推薦使用時機**:
- 準備開發新功能前，評估現有狀態
- 定期專案健康度檢查
- Sprint 結束時的回顧
- 修復大量 Bug 後的驗證
- 用戶反饋分析

**手動使用**:
```bash
使用 Skill: project-audit
```

---

## 審查清單 (Audit Checklist)

### 1. 交友軟體核心功能

| 功能 | 狀態 | 說明 |
|-----|------|-----|
| 用戶註冊/登入 | 查看 [核心功能狀態](resources/feature-status.md) | 包含 Email 驗證、密碼重設 |
| 個人檔案管理 | 查看 [核心功能狀態](resources/feature-status.md) | 照片、興趣標籤、自我介紹 |
| 探索/瀏覽用戶 | 查看 [核心功能狀態](resources/feature-status.md) | 配對分數、篩選條件 |
| 喜歡/跳過機制 | 查看 [核心功能狀態](resources/feature-status.md) | 滑動卡片交互 |
| 配對系統 | 查看 [核心功能狀態](resources/feature-status.md) | 互相喜歡即配對 |
| 即時聊天 | 查看 [核心功能狀態](resources/feature-status.md) | WebSocket 訊息 |
| 封鎖/舉報 | 查看 [核心功能狀態](resources/feature-status.md) | 安全防護機制 |
| 通知系統 | 查看 [核心功能狀態](resources/feature-status.md) | 即時 + 持久化 |
| 管理後台 | 查看 [核心功能狀態](resources/feature-status.md) | 舉報處理、內容審核 |

### 2. 前後端功能對應檢查

查看 [前後端差異分析](resources/frontend-backend-gap.md)

### 3. 已知問題和潛在 Bug

查看 [已知問題清單](resources/known-issues.md)

### 4. 改進建議

查看 [改進建議](resources/improvement-suggestions.md)

---

## 審查流程

### 第一步：功能完整性檢查

```bash
# 1. 檢查後端 API 模組
ls backend/app/api/

# 2. 檢查前端頁面和組件
ls frontend/src/views/
ls frontend/src/components/
ls frontend/src/stores/

# 3. 檢查路由配置
cat frontend/src/router/index.js
```

### 第二步：前後端對應分析

```bash
# 1. 列出所有後端 API 端點
grep -r "@router\." backend/app/api/ --include="*.py"

# 2. 列出前端所有 API 呼叫
grep -r "apiClient\." frontend/src/ --include="*.js" --include="*.vue"

# 3. 比較差異
```

### 第三步：測試驗證

```bash
# 1. 執行後端測試
cd backend && pytest -v --cov=app

# 2. 執行前端測試
cd frontend && npm run test

# 3. 使用 Chrome DevTools MCP 進行 E2E 測試
# 參考 resources/e2e-testing-guide.md
```

### 第四步：流程測試

使用 Chrome DevTools MCP 進行完整用戶流程測試：

1. **註冊流程**: 註冊 → 驗證 Email → 建立檔案
2. **配對流程**: 瀏覽 → 喜歡 → 配對
3. **聊天流程**: 配對列表 → 開始聊天 → 發送訊息
4. **安全流程**: 封鎖用戶 → 舉報用戶

---

## 資源檔案

| 檔案 | 說明 |
|-----|------|
| [feature-status.md](resources/feature-status.md) | 核心功能實現狀態 |
| [frontend-backend-gap.md](resources/frontend-backend-gap.md) | 前後端功能差異分析 |
| [known-issues.md](resources/known-issues.md) | 已知問題和潛在 Bug |
| [improvement-suggestions.md](resources/improvement-suggestions.md) | 改進建議和優先級 |
| [e2e-testing-guide.md](resources/e2e-testing-guide.md) | E2E 測試指南 |

---

## 相關 Skills

- **mergemeet-quickstart** - 完整開發指南
- **backend-dev-fastapi** - 後端開發規範
- **frontend-dev-vue3** - 前端開發規範
- **api-routing-standards** - API 路由規範
- **testing-guide** - 測試策略

---

## 查詢外部文檔 (Context7 MCP)

需要查詢技術文檔時：

```bash
# Vue 3 相關
context7: resolve-library-id "vue"
context7: get-library-docs "/vue" topic="composition api"

# FastAPI 相關
context7: resolve-library-id "fastapi"
context7: get-library-docs "/fastapi" topic="websocket"

# Pinia 狀態管理
context7: resolve-library-id "pinia"
context7: get-library-docs "/pinia" topic="stores"
```

---

## 審查輸出模板

完成審查後，請使用以下模板整理結果：

```markdown
# MergeMeet 專案審查報告

## 審查日期: YYYY-MM-DD

## 1. 功能完整性 (X/10)
- [x] 已實現功能列表
- [ ] 缺失功能列表

## 2. 前後端一致性
- 後端有前端無: X 個
- 前端有後端無: X 個
- 詳細清單: ...

## 3. 發現問題
### 嚴重 (P0)
- ...
### 中等 (P1)
- ...
### 輕微 (P2)
- ...

## 4. 改進建議
### 優先實現
1. ...
2. ...

### 可選改進
1. ...

## 5. 下一步行動
- [ ] 任務 1
- [ ] 任務 2
```

---

**Skill 狀態**: COMPLETE
**強制等級**: ADVISORY
**優先級**: MEDIUM
