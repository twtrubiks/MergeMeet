# 配對列表轉圈圈問題診斷指南

## 問題描述
訪問 http://localhost:5173/matches 時一直顯示 loading 轉圈圈。

## 已確認的正常狀態
✅ 後端 API `/api/discovery/matches` 運作正常 (HTTP 200)
✅ 後端能正確返回配對數據
✅ 前端路由配置正確
✅ Vite proxy 配置正確

## 診斷步驟

### 步驟 1: 檢查瀏覽器開發者工具

1. 打開瀏覽器 (Chrome/Firefox/Edge)
2. 按 F12 打開開發者工具
3. 切換到 **Console** 標籤
4. 重新載入 `/matches` 頁面
5. 查看是否有紅色錯誤訊息

**常見錯誤:**
- `Network Error` - 網絡連接問題
- `401 Unauthorized` - Token 認證失敗
- `CORS error` - 跨域問題
- `timeout` - 請求超時

### 步驟 2: 檢查網絡請求

1. 開發者工具切換到 **Network** 標籤
2. 重新載入 `/matches` 頁面
3. 找到 `matches` 請求（URL 應該是 `/api/discovery/matches`）
4. 檢查:
   - Status: 應該是 `200`
   - Headers: 檢查是否有 `Authorization: Bearer <token>`
   - Response: 檢查返回的數據

**如果看到:**
- `307 Temporary Redirect` - URL 格式問題（前端加了不該有的斜線）
- `401` - Token 失效，需要重新登入
- `Pending` 或卡住 - 網絡問題或超時

### 步驟 3: 檢查 localStorage 中的 Token

在 Console 標籤中執行:
```javascript
console.log('access_token:', localStorage.getItem('access_token'))
console.log('refresh_token:', localStorage.getItem('refresh_token'))
```

如果返回 `null`，表示 token 丟失，需要重新登入。

### 步驟 4: 手動測試 Store

在 Console 標籤中執行:
```javascript
// 獲取 discovery store
const { useDiscoveryStore } = await import('/src/stores/discovery.js')
const store = useDiscoveryStore()

// 檢查狀態
console.log('loading:', store.loading)
console.log('error:', store.error)
console.log('matches:', store.matches)

// 手動觸發請求
store.fetchMatches()
  .then(() => console.log('✅ 成功:', store.matches))
  .catch(err => console.error('❌ 失敗:', err))
```

### 步驟 5: 檢查後端服務狀態

確認後端服務正在運行:
```bash
curl http://localhost:8000/health
```

應該返回:
```json
{
  "status": "healthy",
  "service": "MergeMeet API",
  "version": "1.0.0"
}
```

## 常見問題與解決方案

### 問題 1: Token 失效
**症狀:** Network 標籤看到 401 錯誤

**解決:**
1. 清除瀏覽器的 localStorage
2. 重新登入

```javascript
// 在 Console 執行
localStorage.clear()
window.location.href = '/login'
```

### 問題 2: CORS 問題
**症狀:** Console 看到 CORS 錯誤

**解決:**
檢查 Vite 是否正在運行在正確的 port (5173)，後端在 8000

### 問題 3: 請求超時
**症狀:** 請求一直 Pending，10 秒後失敗

**解決:**
檢查後端服務是否正常運行:
```bash
# 檢查 uvicorn 是否在運行
ps aux | grep uvicorn

# 重啟後端
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 問題 4: 數據庫連接問題
**症狀:** 後端 API 返回 500 錯誤

**解決:**
檢查 Docker 容器狀態:
```bash
docker compose ps
docker compose logs db
```

確保 PostgreSQL 正在運行:
```bash
docker compose up -d
```

## 快速修復嘗試

### 方法 1: 完全重新登入
```javascript
// 在瀏覽器 Console 執行
localStorage.clear()
window.location.href = '/login'
```

### 方法 2: 檢查前端服務
```bash
# 重啟前端服務
cd frontend
npm run dev
```

### 方法 3: 檢查後端服務
```bash
# 重啟後端服務
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 獲取詳細日誌

如果上述步驟都無法解決，請執行:

```bash
# 1. 運行測試腳本
./test_matches_api.sh

# 2. 檢查後端日誌
# (在 uvicorn 運行的終端查看)

# 3. 在瀏覽器 Console 執行完整診斷
console.log('=== MergeMeet 診斷 ===')
console.log('Token:', localStorage.getItem('access_token') ? '存在' : '缺失')
console.log('URL:', window.location.href)

const { useDiscoveryStore } = await import('/src/stores/discovery.js')
const store = useDiscoveryStore()
console.log('Store 狀態:', {
  loading: store.loading,
  error: store.error,
  matchesCount: store.matches.length
})
```

請將以上輸出提供給開發人員協助診斷。
