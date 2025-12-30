# 開發工具

> Claude 已內建 Context7 和 Chrome DevTools MCP 的使用能力。本文件僅記錄專案特有的使用場景。

---

## Context7 常用查詢

### 後端

```bash
# FastAPI
context7: get-library-docs "/fastapi" topic="routing"
context7: get-library-docs "/fastapi" topic="websocket"
context7: get-library-docs "/fastapi" topic="dependencies"

# SQLAlchemy Async
context7: get-library-docs "/sqlalchemy" topic="async session"
context7: get-library-docs "/sqlalchemy" topic="relationship loading"

# Pydantic
context7: get-library-docs "/pydantic" topic="validation"
```

### 前端

```bash
# Vue 3
context7: get-library-docs "/vuejs/core" topic="composition api"
context7: get-library-docs "/vuejs/core" topic="reactivity"

# Pinia
context7: get-library-docs "/vuejs/pinia" topic="actions"

# Vue Router
context7: get-library-docs "/vuejs/router" topic="navigation guards"
```

---

## Chrome DevTools 調試

### 404 錯誤排查

1. Network 標籤 → 找到失敗請求
2. 檢查 Request URL 是否有尾隨斜線
   ```
   ❌ http://localhost:8000/api/profile/
   ✅ http://localhost:8000/api/profile
   ```
3. 修復前端 axios 呼叫

### 認證問題排查

1. Application → LocalStorage → 檢查 `token`
2. Network → 選擇請求 → Headers → 檢查 `Authorization`
3. 若 Token 無效：Console 執行 `localStorage.removeItem('token')`

### Vue 狀態檢查

1. Vue DevTools → Components → 查看 props/state
2. Vue DevTools → Pinia → 查看 store 狀態
3. Console 手動觸發：
   ```javascript
   const store = useProfileStore()
   await store.fetchProfile()
   ```
