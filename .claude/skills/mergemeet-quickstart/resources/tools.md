# Context7 與 Chrome DevTools 使用指南

## 目錄

- [Context7 MCP](#context7-mcp)
- [Chrome DevTools MCP](#chrome-devtools-mcp)
- [常見使用場景](#常見使用場景)

---

## Context7 MCP

### 什麼是 Context7？

Context7 是一個 MCP (Model Context Protocol) 伺服器，讓 Claude Code 能夠即時查詢各種程式庫的官方文檔。

### 基本使用流程

```bash
# 步驟 1: 解析 library ID
context7: resolve-library-id "fastapi"

# 步驟 2: 查詢文檔
context7: get-library-docs "/fastapi" topic="routing"
```

### 常用 Library IDs

#### 後端框架

```bash
# FastAPI
context7: resolve-library-id "fastapi"
context7: get-library-docs "/fastapi" topic="routing"
context7: get-library-docs "/fastapi" topic="dependencies"
context7: get-library-docs "/fastapi" topic="websocket"
context7: get-library-docs "/fastapi" topic="testing"
context7: get-library-docs "/fastapi" topic="background tasks"

# SQLAlchemy
context7: resolve-library-id "sqlalchemy"
context7: get-library-docs "/sqlalchemy" topic="async orm"
context7: get-library-docs "/sqlalchemy" topic="relationships"
context7: get-library-docs "/sqlalchemy" topic="queries"
context7: get-library-docs "/sqlalchemy" topic="migrations"

# Pydantic
context7: resolve-library-id "pydantic"
context7: get-library-docs "/pydantic" topic="validation"
context7: get-library-docs "/pydantic" topic="field types"
context7: get-library-docs "/pydantic" topic="model config"
```

#### 前端框架

```bash
# Vue 3
context7: resolve-library-id "vue"
context7: get-library-docs "/vuejs/core" topic="composition api"
context7: get-library-docs "/vuejs/core" topic="reactivity"
context7: get-library-docs "/vuejs/core" topic="lifecycle hooks"
context7: get-library-docs "/vuejs/core" topic="template syntax"
context7: get-library-docs "/vuejs/core" topic="component props"

# Pinia
context7: resolve-library-id "pinia"
context7: get-library-docs "/vuejs/pinia" topic="state"
context7: get-library-docs "/vuejs/pinia" topic="actions"
context7: get-library-docs "/vuejs/pinia" topic="getters"
context7: get-library-docs "/vuejs/pinia" topic="composition api"

# Vue Router
context7: resolve-library-id "vue-router"
context7: get-library-docs "/vuejs/router" topic="navigation"
context7: get-library-docs "/vuejs/router" topic="route guards"
context7: get-library-docs "/vuejs/router" topic="dynamic routing"
```

#### 工具庫

```bash
# Axios
context7: resolve-library-id "axios"
context7: get-library-docs "/axios/axios" topic="requests"
context7: get-library-docs "/axios/axios" topic="interceptors"

# Redis
context7: resolve-library-id "redis"
context7: get-library-docs "/redis/redis-py" topic="async"

# pytest
context7: resolve-library-id "pytest"
context7: get-library-docs "/pytest-dev/pytest" topic="fixtures"
context7: get-library-docs "/pytest-dev/pytest" topic="parametrize"
```

### Mode 選項

**code mode**（預設）- 程式碼範例和 API 參考

```bash
context7: get-library-docs "/fastapi" topic="routing" mode="code"
```

**info mode** - 概念性文檔和架構說明

```bash
context7: get-library-docs "/fastapi" topic="async" mode="info"
```

### 實用範例

#### 場景 1: 學習 FastAPI 路由

```bash
# 1. 查詢路由基礎
context7: get-library-docs "/fastapi" topic="routing"

# 2. 查詢路徑參數
context7: get-library-docs "/fastapi" topic="path parameters"

# 3. 查詢查詢參數
context7: get-library-docs "/fastapi" topic="query parameters"

# 4. 查詢請求體
context7: get-library-docs "/fastapi" topic="request body"

# 5. 查詢回應模型
context7: get-library-docs "/fastapi" topic="response model"
```

#### 場景 2: 學習 Vue 3 Composition API

```bash
# 1. Composition API 基礎
context7: get-library-docs "/vuejs/core" topic="composition api" mode="info"

# 2. ref 和 reactive
context7: get-library-docs "/vuejs/core" topic="reactivity fundamentals"

# 3. computed
context7: get-library-docs "/vuejs/core" topic="computed"

# 4. watch 和 watchEffect
context7: get-library-docs "/vuejs/core" topic="watchers"

# 5. lifecycle hooks
context7: get-library-docs "/vuejs/core" topic="lifecycle hooks"
```

#### 場景 3: 學習 SQLAlchemy 2.0 Async

```bash
# 1. 異步 ORM 概述
context7: get-library-docs "/sqlalchemy" topic="asyncio" mode="info"

# 2. 異步 session
context7: get-library-docs "/sqlalchemy" topic="async session"

# 3. 異步查詢
context7: get-library-docs "/sqlalchemy" topic="async queries" mode="code"

# 4. 關聯查詢
context7: get-library-docs "/sqlalchemy" topic="relationship loading"
```

---

## Chrome DevTools MCP

### 什麼是 Chrome DevTools MCP？

Chrome DevTools MCP 允許 Claude Code 透過瀏覽器開發者工具檢查和測試前端應用。

### 使用前提

1. 前端應用正在運行: http://localhost:5173
2. Chrome 瀏覽器已打開
3. 開發者工具已啟用 (F12)

### 核心功能

#### 1. Console 檢查

**用途**: 查看 JavaScript 錯誤和日誌

**使用方法**:
1. 打開 http://localhost:5173
2. 按 F12 打開 DevTools
3. 切換到 Console 標籤
4. 檢查是否有紅色錯誤訊息

**常見錯誤**:
```javascript
// ❌ 未定義的變數
Uncaught ReferenceError: user is not defined

// ❌ 類型錯誤
Uncaught TypeError: Cannot read property 'name' of undefined

// ❌ API 請求錯誤
Error: Request failed with status code 404

// ❌ CORS 錯誤
Access to XMLHttpRequest blocked by CORS policy
```

#### 2. Network 檢查

**用途**: 監控 API 請求和回應

**檢查項目**:

**URL 格式**:
```
✅ http://localhost:8000/api/profile          (正確 - 無斜線)
❌ http://localhost:8000/api/profile/         (錯誤 - 有斜線)
```

**狀態碼**:
```
✅ 200 OK                 (成功)
✅ 201 Created            (創建成功)
✅ 204 No Content         (刪除成功)
❌ 400 Bad Request        (請求錯誤)
❌ 401 Unauthorized       (未授權)
❌ 404 Not Found          (找不到)
❌ 500 Internal Error     (伺服器錯誤)
```

**Headers 檢查**:
```
Request Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  Content-Type: application/json

Response Headers:
  Content-Type: application/json
  Access-Control-Allow-Origin: http://localhost:5173
```

**Payload 檢查**:
```json
// Request Payload
{
  "email": "test@example.com",
  "password": "password123"
}

// Response
{
  "id": "123",
  "email": "test@example.com",
  "access_token": "eyJ..."
}
```

#### 3. Application 檢查

**LocalStorage**:
```javascript
// 查看儲存的 Token
localStorage.getItem('token')

// 查看用戶資訊
localStorage.getItem('user')

// 清除 LocalStorage
localStorage.clear()
```

**Cookies**:
```
Name: session_id
Value: abc123...
Domain: localhost
Path: /
Expires: 2024-12-31
HttpOnly: true
```

**Service Workers**:
```
Status: Activated and Running
Scope: http://localhost:5173/
```

#### 4. Vue DevTools

**安裝**: Chrome Extension - Vue.js devtools

**功能**:

**Components 樹狀圖**:
```
App
├── Header
├── MainView
│   ├── ProfileCard
│   └── PhotoGallery
└── Footer
```

**Pinia Stores**:
```
authStore:
  state:
    user: { id: '123', email: 'test@example.com' }
    isAuthenticated: true
    token: 'eyJ...'

profileStore:
  state:
    profile: { bio: '...', interests: [...] }
    photos: [...]
```

**Events 追蹤**:
```
Event: update:profile
Payload: { bio: 'New bio' }
Source: ProfileForm.vue
Target: ProfileCard.vue
```

---

## 常見使用場景

### 場景 1: 調試 404 錯誤

```bash
# 1. 在 Network 標籤找到失敗的請求
# 2. 檢查 Request URL
Request URL: http://localhost:8000/api/profile/
                                                ^ 多餘的斜線！

# 3. 修復前端程式碼
// ❌ 錯誤
await axios.get('/api/profile/')

// ✅ 正確
await axios.get('/api/profile')

# 4. 參考官方文檔
context7: get-library-docs "/fastapi" topic="routing"

# 5. 使用 Skill
使用 Skill: api-routing-standards
```

### 場景 2: 調試認證問題

```bash
# 1. 檢查 LocalStorage 是否有 Token
# DevTools > Application > LocalStorage
localStorage.getItem('token')  // 應該返回 JWT token

# 2. 檢查 Network 請求的 Headers
# DevTools > Network > 選擇請求 > Headers
Authorization: Bearer eyJ...  // 應該存在

# 3. 如果 Token 無效，重新登入
# Console:
localStorage.removeItem('token')
// 然後重新登入

# 4. 查詢 JWT 相關文檔
context7: get-library-docs "/fastapi" topic="security oauth2"
```

### 場景 3: 調試 Vue 組件狀態

```bash
# 1. 打開 Vue DevTools
# DevTools > Vue 標籤

# 2. 選擇組件查看 props 和 state
<ProfileCard>
  props:
    user: { id: '123', name: 'John' }
  data:
    isEditing: false

# 3. 檢查 Pinia store
profileStore:
  state:
    profile: null  // ← 為什麼是 null？

# 4. 在 Console 手動觸發 action
import { useProfileStore } from '@/stores/profile'
const store = useProfileStore()
await store.fetchProfile()

# 5. 查詢 Pinia 文檔
context7: get-library-docs "/vuejs/pinia" topic="state"
```

### 場景 4: 學習新的 API

```bash
# 1. 先查詢官方文檔了解概念
context7: get-library-docs "/fastapi" topic="websocket" mode="info"

# 2. 查看程式碼範例
context7: get-library-docs "/fastapi" topic="websocket" mode="code"

# 3. 實作並在 Console 測試
const ws = new WebSocket('ws://localhost:8000/ws')
ws.onopen = () => console.log('Connected')
ws.onmessage = (event) => console.log('Message:', event.data)

# 4. 在 Network 標籤查看 WebSocket 連接
# DevTools > Network > WS 標籤
```

### 場景 5: 效能優化

```bash
# 1. 使用 Performance 標籤記錄
# DevTools > Performance > Record

# 2. 檢查 Network 的 Waterfall
# 找出慢的請求

# 3. 查詢優化文檔
context7: get-library-docs "/vuejs/core" topic="performance" mode="info"
context7: get-library-docs "/fastapi" topic="async" mode="info"

# 4. 在 Console 測試優化後的效果
console.time('fetchData')
await fetchData()
console.timeEnd('fetchData')
```

---

## 最佳實踐

### Context7 使用技巧

1. **先用 info mode 了解概念**
   ```bash
   context7: get-library-docs "/fastapi" topic="dependencies" mode="info"
   ```

2. **再用 code mode 查看範例**
   ```bash
   context7: get-library-docs "/fastapi" topic="dependencies" mode="code"
   ```

3. **查詢時使用具體的 topic**
   ```bash
   # ✅ 具體
   context7: get-library-docs "/fastapi" topic="dependency injection"

   # ❌ 太廣泛
   context7: get-library-docs "/fastapi" topic="fastapi"
   ```

### Chrome DevTools 使用技巧

1. **善用 Console 的 filter**
   - Errors: 只顯示錯誤
   - Warnings: 只顯示警告
   - Info: 顯示資訊

2. **使用 Network 的 filter**
   - XHR: 只顯示 AJAX 請求
   - Doc: 只顯示文檔請求
   - CSS/JS: 只顯示資源請求

3. **善用 Preserve log**
   - 防止頁面重新載入時清除日誌

4. **使用 Disable cache**
   - 在開發時禁用快取，確保看到最新的程式碼

---

**提示**: Context7 和 Chrome DevTools 是開發過程中最強大的工具，善用它們可以大幅提升開發效率！
