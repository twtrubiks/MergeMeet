# 常見問題類型與檢查方法

本文件列出專案審查時常見的問題類型及其檢查方法。

---

## 問題優先級定義

| 等級 | 說明 | 處理時限 |
|-----|------|---------|
| **P0 Critical** | 影響核心功能，系統無法使用 | 立即修復 |
| **P1 High** | 重要功能缺失或損壞 | 優先處理 |
| **P2 Medium** | 用戶體驗問題 | 計劃性處理 |
| **P3 Low** | 優化建議 | 有空再做 |

---

## P0 常見問題類型

### 1. 未導入的依賴

**症狀**：ReferenceError、ImportError

**檢查方法**：
```bash
# 前端：檢查是否有使用但未 import 的變數
npm run build  # 會報錯

# 後端：執行測試
cd backend && pytest
```

**常見案例**：
- 使用 `logger` 但未 import
- 使用工具函數但未導入

### 2. API 路由錯誤

**症狀**：404 Not Found

**檢查方法**：
```bash
# 確認路由定義無尾隨斜線
grep -r "router\.\(get\|post\).*/$" backend/app/api/
```

**MergeMeet 規則**：所有 API 路由禁止尾隨斜線

### 3. 資料庫連線問題

**症狀**：Connection refused、Timeout

**檢查方法**：
```bash
# 確認資料庫服務運行
docker compose ps

# 測試連線
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c "SELECT 1"
```

---

## P1 常見問題類型

### 1. 前後端資料格式不一致

**症狀**：欄位缺失、類型錯誤

**檢查方法**：
1. 比對後端 Pydantic schema
2. 比對前端發送的 payload
3. 使用 Chrome DevTools Network 檢視

**常見問題**：
- snake_case vs camelCase
- 檔案大小限制不一致
- 日期格式不一致

### 2. 功能缺失

**症狀**：UI 存在但功能不完整

**檢查清單**：
- [ ] 後端 API 存在
- [ ] 前端有呼叫 API
- [ ] 錯誤處理完整
- [ ] 成功回饋顯示

### 3. 權限驗證缺失

**症狀**：未登入可存取受保護資源

**檢查方法**：
```bash
# 後端：確認路由有 Depends(get_current_user)
grep -r "get_current_user" backend/app/api/

# 前端：確認路由有 meta.requiresAuth
grep -r "requiresAuth" frontend/src/router/
```

---

## P2 常見問題類型

### 1. 缺少載入狀態

**症狀**：操作時無回饋，用戶體驗差

**檢查方法**：
```javascript
// 確認有 loading 狀態
grep -r "loading" frontend/src/views/
```

### 2. 缺少錯誤處理

**症狀**：錯誤時無提示或顯示原始錯誤

**檢查方法**：
```javascript
// 確認 catch 區塊有處理
grep -r "catch.*error" frontend/src/
```

### 3. Bundle Size 過大

**症狀**：首次載入緩慢

**檢查方法**：
```bash
cd frontend && npm run build
# 檢查輸出的檔案大小
```

**建議**：主 bundle 應小於 500KB (gzip 前)

---

## 檢查腳本

### Python 語法檢查

```bash
cd backend
python -m py_compile app/**/*.py
```

### 前端 Build 檢查

```bash
cd frontend
npm run build 2>&1 | grep -E "(error|warning)"
```

### 測試執行

```bash
# 後端
cd backend && pytest -v --tb=short

# 前端
cd frontend && npm run test
```

---

## 問題檢查清單

### 程式碼品質

- [ ] 無語法錯誤
- [ ] 無未使用的 import
- [ ] 無未定義的變數
- [ ] Build 成功無錯誤

### 功能完整性

- [ ] 所有 CRUD 操作可正常執行
- [ ] 錯誤有適當處理和顯示
- [ ] 載入狀態有顯示
- [ ] 成功操作有回饋

### 安全性

- [ ] 敏感路由有權限驗證
- [ ] 密碼不以明文儲存
- [ ] API 有 rate limiting（如適用）
- [ ] 檔案上傳有類型和大小驗證

### 效能

- [ ] 無 N+1 查詢問題
- [ ] 適當使用快取
- [ ] Bundle size 合理
- [ ] 圖片有適當壓縮

---

## 問題回報模板

發現問題時使用以下格式記錄：

```markdown
## 問題標題

**優先級**: P0/P1/P2/P3

**檔案位置**: `path/to/file.py:123`

**問題描述**:
簡述問題

**重現步驟**:
1. 步驟一
2. 步驟二

**預期行為**:
應該發生什麼

**實際行為**:
實際發生什麼

**建議修復方案**:
如何修復
```
