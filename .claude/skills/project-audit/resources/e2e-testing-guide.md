# E2E 測試指南（使用 Chrome DevTools MCP）

> 本指南說明如何使用 Chrome DevTools MCP 進行端對端測試

## 準備工作

### 1. 啟動服務

```bash
# 終端 1: 啟動資料庫和 Redis
docker compose up -d

# 終端 2: 啟動後端
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 終端 3: 啟動前端
cd frontend && npm run dev
```

### 2. 確認 Chrome DevTools MCP 可用

```bash
# 列出可用頁面
mcp__chrome-devtools__list_pages
```

---

## 測試流程

### 流程 1: 用戶註冊

```bash
# 1. 打開註冊頁面
mcp__chrome-devtools__navigate_page url="http://localhost:5173/register"

# 2. 獲取頁面快照
mcp__chrome-devtools__take_snapshot

# 3. 填寫表單
mcp__chrome-devtools__fill_form elements=[
  {"uid": "email-input-uid", "value": "test@example.com"},
  {"uid": "password-input-uid", "value": "SecurePass123!"},
  {"uid": "confirm-password-uid", "value": "SecurePass123!"},
  {"uid": "dob-input-uid", "value": "2000-01-01"}
]

# 4. 點擊註冊按鈕
mcp__chrome-devtools__click uid="register-button-uid"

# 5. 等待結果
mcp__chrome-devtools__wait_for text="註冊成功"

# 6. 檢查網路請求
mcp__chrome-devtools__list_network_requests resourceTypes=["fetch"]
```

**驗證點**:
- [ ] 表單驗證錯誤訊息正確顯示
- [ ] 註冊成功後跳轉到正確頁面
- [ ] API 請求返回 201 狀態碼

---

### 流程 2: 用戶登入

```bash
# 1. 打開登入頁面
mcp__chrome-devtools__navigate_page url="http://localhost:5173/login"

# 2. 填寫憑證
mcp__chrome-devtools__fill uid="email-input" value="test@example.com"
mcp__chrome-devtools__fill uid="password-input" value="SecurePass123!"

# 3. 點擊登入
mcp__chrome-devtools__click uid="login-button"

# 4. 等待跳轉
mcp__chrome-devtools__wait_for text="探索配對"
```

**驗證點**:
- [ ] 錯誤密碼顯示正確訊息
- [ ] 登入成功後跳轉到首頁或探索頁
- [ ] Cookie 正確設置

---

### 流程 3: 建立個人檔案

```bash
# 1. 導航到個人檔案頁
mcp__chrome-devtools__navigate_page url="http://localhost:5173/profile"

# 2. 獲取頁面狀態
mcp__chrome-devtools__take_snapshot

# 3. 填寫基本資料
mcp__chrome-devtools__fill uid="display-name" value="測試用戶"
mcp__chrome-devtools__fill uid="bio" value="這是測試用的自我介紹"
mcp__chrome-devtools__click uid="gender-female"

# 4. 選擇興趣標籤（至少 3 個）
mcp__chrome-devtools__click uid="interest-tag-1"
mcp__chrome-devtools__click uid="interest-tag-2"
mcp__chrome-devtools__click uid="interest-tag-3"

# 5. 儲存
mcp__chrome-devtools__click uid="save-button"

# 6. 驗證成功
mcp__chrome-devtools__wait_for text="儲存成功"
```

**驗證點**:
- [ ] 必填欄位驗證
- [ ] 興趣標籤數量限制（3-10）
- [ ] 儲存成功提示

---

### 流程 4: 探索配對

```bash
# 1. 導航到探索頁
mcp__chrome-devtools__navigate_page url="http://localhost:5173/discovery"

# 2. 等待載入
mcp__chrome-devtools__wait_for text="探索配對"

# 3. 獲取候選人卡片
mcp__chrome-devtools__take_snapshot

# 4. 測試喜歡
mcp__chrome-devtools__click uid="like-button"

# 5. 測試跳過
mcp__chrome-devtools__click uid="pass-button"

# 6. 檢查網路請求
mcp__chrome-devtools__list_network_requests
```

**驗證點**:
- [ ] 候選人卡片正確顯示
- [ ] 喜歡/跳過操作正常
- [ ] 無更多候選人時顯示正確訊息
- [ ] 配對成功彈窗

---

### 流程 5: 聊天功能

```bash
# 1. 導航到訊息列表
mcp__chrome-devtools__navigate_page url="http://localhost:5173/messages"

# 2. 點擊一個配對
mcp__chrome-devtools__click uid="match-item-0"

# 3. 等待聊天頁面載入
mcp__chrome-devtools__wait_for text="發送"

# 4. 發送訊息
mcp__chrome-devtools__fill uid="message-input" value="你好！"
mcp__chrome-devtools__click uid="send-button"

# 5. 驗證訊息出現
mcp__chrome-devtools__wait_for text="你好！"

# 6. 檢查 WebSocket 連接
mcp__chrome-devtools__list_network_requests resourceTypes=["websocket"]
```

**驗證點**:
- [ ] 配對列表正確顯示
- [ ] 訊息發送成功
- [ ] 即時收到回覆（如果對方在線）
- [ ] 已讀狀態正確顯示

---

### 流程 6: 封鎖和舉報

```bash
# 1. 在探索頁找到舉報按鈕
mcp__chrome-devtools__navigate_page url="http://localhost:5173/discovery"

# 2. 點擊舉報按鈕
mcp__chrome-devtools__click uid="report-button"

# 3. 填寫舉報表單
mcp__chrome-devtools__fill uid="report-reason" value="HARASSMENT"
mcp__chrome-devtools__fill uid="report-detail" value="測試舉報"
mcp__chrome-devtools__click uid="submit-report"

# 4. 驗證舉報成功
mcp__chrome-devtools__wait_for text="舉報成功"
```

**驗證點**:
- [ ] 舉報彈窗正確顯示
- [ ] 舉報成功後自動跳過該用戶
- [ ] 封鎖列表正確更新

---

### 流程 7: 管理後台

```bash
# 1. 管理員登入
mcp__chrome-devtools__navigate_page url="http://localhost:5173/admin/login"
mcp__chrome-devtools__fill uid="email" value="admin@mergemeet.com"
mcp__chrome-devtools__fill uid="password" value="admin-password"
mcp__chrome-devtools__click uid="login"

# 2. 等待跳轉到管理後台
mcp__chrome-devtools__wait_for text="管理後台"

# 3. 檢查統計數據
mcp__chrome-devtools__take_snapshot

# 4. 處理舉報
mcp__chrome-devtools__click uid="reports-tab"
mcp__chrome-devtools__wait_for text="舉報管理"

# 5. 審核照片
mcp__chrome-devtools__click uid="photo-moderation-tab"
mcp__chrome-devtools__wait_for text="照片審核"
```

**驗證點**:
- [ ] 統計數據正確
- [ ] 舉報列表載入
- [ ] 審核操作正常

---

## 錯誤檢測

### 檢查控制台錯誤

```bash
# 獲取控制台訊息
mcp__chrome-devtools__list_console_messages types=["error", "warn"]

# 查看特定錯誤詳情
mcp__chrome-devtools__get_console_message msgid=123
```

### 檢查網路錯誤

```bash
# 列出所有請求
mcp__chrome-devtools__list_network_requests

# 獲取特定請求詳情
mcp__chrome-devtools__get_network_request reqid=456
```

---

## 截圖證據

```bash
# 截取整頁
mcp__chrome-devtools__take_screenshot fullPage=true filePath="./docs/screenshots/test-result.png"

# 截取特定元素
mcp__chrome-devtools__take_screenshot uid="error-message" filePath="./docs/screenshots/error.png"
```

---

## 測試報告模板

```markdown
# E2E 測試報告

## 測試日期: YYYY-MM-DD

## 環境
- 前端: http://localhost:5173
- 後端: http://localhost:8000
- 瀏覽器: Chrome

## 測試結果

| 流程 | 狀態 | 備註 |
|-----|:----:|-----|
| 用戶註冊 | PASS/FAIL | |
| 用戶登入 | PASS/FAIL | |
| 建立檔案 | PASS/FAIL | |
| 探索配對 | PASS/FAIL | |
| 聊天功能 | PASS/FAIL | |
| 封鎖舉報 | PASS/FAIL | |
| 管理後台 | PASS/FAIL | |

## 發現問題

### 問題 1
- 描述: ...
- 截圖: ...
- 重現步驟: ...

## 控制台錯誤
- [列出發現的控制台錯誤]

## 網路錯誤
- [列出失敗的 API 請求]
```

---

## 自動化測試腳本

對於重複性測試，可以建立 Claude Code 命令：

```bash
# .claude/commands/e2e-test.md
執行完整的 E2E 測試流程：
1. 啟動服務
2. 執行各流程測試
3. 收集錯誤
4. 產生報告
```
