---
name: project-audit
description: 評估 MergeMeet 專案健康狀態時使用此 skill。協助檢查功能完整性、前後端一致性、潛在錯誤和用戶流程邏輯。適用於開發新功能前或 sprint 審查時。
---

# 專案審查

## 目的

全面檢查 MergeMeet 交友平台的健康狀態，確保：
1. 交友應用程式的功能完整性
2. 前後端 API 一致性
3. 錯誤檢測
4. 用戶流程邏輯

---

## 審查檢查清單

### 核心交友應用功能

| 類別 | 檢查點 |
|------|--------|
| 認證 | 註冊、登入、Email 驗證、密碼重設 |
| 個人檔案 | 編輯、照片上傳、審核、興趣 |
| 探索 | 瀏覽候選人、喜歡/跳過、偏好設定 |
| 聊天 | 即時訊息、已讀狀態、內容審核 |
| 安全 | 封鎖、舉報、舉報記錄 |
| 通知 | 即時通知、通知中心 |
| 管理後台 | 儀表板、舉報處理、用戶管理 |

### 前後端一致性

檢查 API 端點和前端呼叫的一致性：

```bash
# 列出所有後端 API 端點
grep -r "@router\." backend/app/api/ --include="*.py"

# 列出所有前端 API 呼叫
grep -r "axios\." frontend/src/ --include="*.js" --include="*.vue"
```

### 測試

```bash
# 執行含覆蓋率的後端測試
cd backend && pytest -v --cov=app

# 執行前端測試
cd frontend && npm run test
```

---

## 審查流程

### 步驟 1：功能完整性

```bash
# 檢查後端 API 模組
ls backend/app/api/

# 檢查前端頁面和組件
ls frontend/src/views/
ls frontend/src/components/
ls frontend/src/stores/
```

### 步驟 2：前後端差異分析

比較 API 端點和前端呼叫以識別：
- 後端有 API 但前端未實現
- 前端呼叫但後端不存在的 API

### 步驟 3：用戶流程測試

測試完整的用戶流程：
1. **註冊**: 註冊 → Email 驗證 → 建立檔案
2. **配對**: 瀏覽 → 喜歡 → 配對
3. **聊天**: 配對列表 → 開始聊天 → 發送訊息
4. **安全**: 封鎖用戶 → 舉報用戶

---

## 參考資料

| 主題 | 檔案 |
|------|------|
| 功能狀態 | [feature-status.md](references/feature-status.md) |
| 前後端差異 | [frontend-backend-gap.md](references/frontend-backend-gap.md) |
| 已知問題 | [known-issues.md](references/known-issues.md) |
| 改進建議 | [improvement-suggestions.md](references/improvement-suggestions.md) |
| E2E 測試指南 | [e2e-testing-guide.md](references/e2e-testing-guide.md) |

---

## 審查報告範本

```markdown
# MergeMeet 專案審查報告

## 日期: YYYY-MM-DD

## 1. 功能完整性 (X/10)
- [x] 已實現的功能
- [ ] 缺失的功能

## 2. 前後端一致性
- 後端有但前端無: X 項
- 前端有但後端無: X 項

## 3. 發現的問題
### 嚴重 (P0)
- ...
### 中等 (P1)
- ...
### 輕微 (P2)
- ...

## 4. 建議
1. ...
2. ...

## 5. 下一步
- [ ] 任務 1
- [ ] 任務 2
```

---

## 相關 Skills

- **mergemeet-quickstart** - 開發指南
- **backend-dev-fastapi** - 後端標準
- **frontend-dev-vue3** - 前端標準
- **api-routing-standards** - API 路由規則
