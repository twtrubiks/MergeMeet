# E2E 測試指南（Chrome DevTools MCP）

> 使用 Chrome DevTools MCP 進行端對端測試。

---

## 準備工作

```bash
# 啟動服務
docker compose up -d
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
cd frontend && npm run dev

# 確認 MCP 可用
mcp__chrome-devtools__list_pages
```

---

## 核心測試流程

### 1. 用戶註冊登入

```bash
mcp__chrome-devtools__navigate_page url="http://localhost:5173/register"
mcp__chrome-devtools__take_snapshot
mcp__chrome-devtools__fill_form elements=[...]
mcp__chrome-devtools__click uid="register-button"
mcp__chrome-devtools__wait_for text="註冊成功"
```

### 2. 個人檔案

```bash
mcp__chrome-devtools__navigate_page url="http://localhost:5173/profile"
mcp__chrome-devtools__fill uid="display-name" value="測試用戶"
mcp__chrome-devtools__click uid="save-button"
mcp__chrome-devtools__wait_for text="儲存成功"
```

### 3. 探索配對

```bash
mcp__chrome-devtools__navigate_page url="http://localhost:5173/discovery"
mcp__chrome-devtools__click uid="like-button"
mcp__chrome-devtools__click uid="pass-button"
```

### 4. 聊天功能

```bash
mcp__chrome-devtools__navigate_page url="http://localhost:5173/messages"
mcp__chrome-devtools__click uid="match-item-0"
mcp__chrome-devtools__fill uid="message-input" value="你好！"
mcp__chrome-devtools__click uid="send-button"
```

---

## 錯誤檢測

```bash
# 控制台錯誤
mcp__chrome-devtools__list_console_messages types=["error", "warn"]

# 網路請求
mcp__chrome-devtools__list_network_requests
mcp__chrome-devtools__get_network_request reqid=123

# 截圖
mcp__chrome-devtools__take_screenshot fullPage=true filePath="./screenshot.png"
```

---

## 測試檢查清單

| 流程 | 驗證點 |
|------|--------|
| 註冊 | 表單驗證、成功跳轉、API 201 |
| 登入 | 錯誤訊息、Cookie 設置 |
| 檔案 | 必填驗證、儲存成功 |
| 探索 | 卡片顯示、操作正常 |
| 聊天 | 訊息發送、即時接收 |
