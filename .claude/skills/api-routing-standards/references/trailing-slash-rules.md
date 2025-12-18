# 尾隨斜線規則 (Trailing Slash Rules)

## 🚨 最高優先級規則

**本專案所有 API 端點一律不使用尾隨斜線 (trailing slash)**

違反此規則會直接導致 **404 Not Found** 錯誤！

---

## 為什麼這個規則如此重要？

### FastAPI 配置

```python
# backend/app/main.py
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    redirect_slashes=False,  # ⚠️ 禁用自動重定向
)
```

### 行為說明

| URL | 狀態碼 | 說明 |
|-----|--------|------|
| `/api/profile` | 200 OK | ✅ 正確格式 |
| `/api/profile/` | 404 Not Found | ❌ 錯誤格式 |

**關鍵點**：
- ✅ 不帶斜線的 URL 正常工作
- ❌ 帶斜線的 URL 直接返回 404
- ⚠️ **不會自動重定向** - Authorization Header 會在重定向中丟失

---

## ✅ 正確的路由定義

### 基本路由
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/profile", tags=["Profile"])

# ✅ 正確 - 使用空字串表示根路徑
@router.get("")
async def get_profile():
    """GET /api/profile"""
    pass

@router.post("")
async def create_profile():
    """POST /api/profile"""
    pass
```

### 子路徑路由
```python
# ✅ 正確 - 不使用尾隨斜線
@router.get("/interests")
async def get_interests():
    """GET /api/profile/interests"""
    pass

@router.put("/interests")
async def update_interests():
    """PUT /api/profile/interests"""
    pass

@router.post("/photos")
async def upload_photo():
    """POST /api/profile/photos"""
    pass

@router.delete("/photos/{photo_id}")
async def delete_photo(photo_id: str):
    """DELETE /api/profile/photos/{photo_id}"""
    pass
```

### 所有 API 模組的正確格式

```python
# ===== auth.py =====
router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register")        # POST /api/auth/register
@router.post("/login")           # POST /api/auth/login
@router.post("/refresh")         # POST /api/auth/refresh

# ===== profile.py =====
router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("")                   # GET /api/profile
@router.put("")                   # PUT /api/profile
@router.put("/interests")         # PUT /api/profile/interests
@router.post("/photos")           # POST /api/profile/photos
@router.delete("/photos/{id}")    # DELETE /api/profile/photos/{id}
@router.get("/interest-tags")     # GET /api/profile/interest-tags

# ===== discovery.py =====
router = APIRouter(prefix="/api/discovery", tags=["Discovery"])

@router.get("/browse")            # GET /api/discovery/browse
@router.post("/like/{user_id}")   # POST /api/discovery/like/{id}
@router.post("/pass/{user_id}")   # POST /api/discovery/pass/{id}
@router.get("/matches")           # GET /api/discovery/matches

# ===== messages.py =====
router = APIRouter(prefix="/api/messages", tags=["Messages"])

@router.get("/conversations")                       # GET /api/messages/conversations
@router.get("/matches/{match_id}/messages")         # GET /api/messages/matches/{id}/messages
@router.post("/messages/read")                      # POST /api/messages/messages/read
@router.delete("/messages/{message_id}")            # DELETE /api/messages/messages/{id}

# ===== safety.py =====
router = APIRouter(prefix="/api/safety", tags=["Safety"])

@router.post("/block/{user_id}")  # POST /api/safety/block/{id}
@router.delete("/block/{user_id}") # DELETE /api/safety/block/{id}
@router.get("/blocked")           # GET /api/safety/blocked
@router.post("/report")           # POST /api/safety/report
```

---

## ❌ 錯誤的路由定義

### 常見錯誤 1: 根路徑使用 `/`
```python
# ❌ 錯誤 - 不要使用 "/"
@router.get("/")
async def get_profile():
    """這會導致 GET /api/profile/ → 404"""
    pass

@router.post("/")
async def create_profile():
    """這會導致 POST /api/profile/ → 404"""
    pass

# ✅ 正確 - 使用空字串 ""
@router.get("")
async def get_profile():
    """GET /api/profile → 200"""
    pass
```

### 常見錯誤 2: 子路徑使用尾隨斜線
```python
# ❌ 錯誤
@router.get("/interests/")
@router.put("/interests/")
@router.post("/photos/")
@router.delete("/photos/{photo_id}/")

# ✅ 正確
@router.get("/interests")
@router.put("/interests")
@router.post("/photos")
@router.delete("/photos/{photo_id}")
```

---

## 🎨 前端 Axios 對應

### 正確的前端請求
```javascript
// ===== Profile API =====
// ✅ 正確 - 無尾隨斜線
await axios.get('/api/profile')
await axios.post('/api/profile', data)
await axios.put('/api/profile/interests', { interests })
await axios.post('/api/profile/photos', formData)
await axios.delete(`/api/profile/photos/${photoId}`)
await axios.get('/api/profile/interest-tags')

// ===== Discovery API =====
await axios.get('/api/discovery/browse')
await axios.post(`/api/discovery/like/${userId}`)
await axios.post(`/api/discovery/pass/${userId}`)
await axios.get('/api/discovery/matches')

// ===== Messages API =====
await axios.get('/api/messages/conversations')
await axios.get(`/api/messages/matches/${matchId}/messages`)
await axios.post('/api/messages/messages/read', { messageIds })
await axios.delete(`/api/messages/messages/${messageId}`)

// ===== Safety API =====
await axios.post(`/api/safety/block/${userId}`)
await axios.delete(`/api/safety/block/${userId}`)
await axios.get('/api/safety/blocked')
await axios.post('/api/safety/report', reportData)
```

### 錯誤的前端請求
```javascript
// ❌ 錯誤 - 有尾隨斜線（全部 404）
await axios.get('/api/profile/')                    // 404
await axios.put('/api/profile/interests/', data)    // 404
await axios.get('/api/discovery/browse/')           // 404
await axios.post(`/api/discovery/like/${userId}/`)  // 404
await axios.get('/api/messages/conversations/')     // 404
```

---

## 🧪 如何測試

### 1. 使用 curl 測試
```bash
# ✅ 正確格式 - 應該返回 200
curl -w "\nHTTP: %{http_code}\n" \
  -X GET "http://localhost:8000/api/profile" \
  -H "Authorization: Bearer $TOKEN"
# 輸出: HTTP: 200

# ❌ 錯誤格式 - 會返回 404
curl -w "\nHTTP: %{http_code}\n" \
  -X GET "http://localhost:8000/api/profile/" \
  -H "Authorization: Bearer $TOKEN"
# 輸出: HTTP: 404
```

### 2. 使用 pytest 測試
```python
import pytest
from httpx import AsyncClient

async def test_profile_without_trailing_slash():
    """測試：無尾隨斜線應該成功"""
    response = await client.get("/api/profile")
    assert response.status_code == 200  # ✅ 通過

async def test_profile_with_trailing_slash():
    """測試：有尾隨斜線應該失敗"""
    response = await client.get("/api/profile/")
    assert response.status_code == 404  # ✅ 預期的錯誤

async def test_interests_endpoint():
    """測試：子路徑也不應該有尾隨斜線"""
    # ✅ 正確
    response = await client.put("/api/profile/interests", json={"interests": ["運動"]})
    assert response.status_code == 200

    # ❌ 錯誤
    response = await client.put("/api/profile/interests/", json={"interests": ["運動"]})
    assert response.status_code == 404
```

### 3. 使用 Swagger UI 檢查
訪問 `http://localhost:8000/docs`：
1. 檢查所有端點的 URL
2. 確認都沒有尾隨斜線
3. 測試每個端點的功能

---

## 🔍 檢查現有程式碼

### 搜尋錯誤模式
```bash
# 在 backend 目錄搜尋可能的錯誤
cd backend

# 搜尋 @router.get("/")
grep -r '@router\.get\("\/"\)' app/api/

# 搜尋任何以 / 結尾的路由
grep -r '@router\.\w*\(".*\/"\)' app/api/

# 前端搜尋帶尾隨斜線的 API 呼叫
cd ../frontend
grep -r "axios\.\w*('/api/.*/')" src/
```

---

## 📋 檢查清單

創建或修改路由時，請確認：

- [ ] 後端根路徑使用 `""` 而不是 `"/"`
- [ ] 後端所有子路徑不使用尾隨斜線
- [ ] 前端 axios 請求與後端路由完全匹配
- [ ] pytest 測試中的 URL 無尾隨斜線
- [ ] curl 測試腳本無尾隨斜線
- [ ] Swagger UI 顯示的端點格式正確

---

## 🚨 錯誤排查

### 遇到 404 錯誤？

**症狀**：前端請求返回 404，但路由已定義

**檢查步驟**：

1. **檢查後端路由定義**
   ```python
   # ❌ 這是錯誤的
   @router.get("/")

   # ✅ 應該是這樣
   @router.get("")
   ```

2. **檢查前端請求 URL**
   ```javascript
   // ❌ 錯誤
   await axios.get('/api/profile/')

   // ✅ 正確
   await axios.get('/api/profile')
   ```

3. **檢查 FastAPI 配置**
   ```python
   # 確認 main.py 中有這個配置
   app = FastAPI(redirect_slashes=False)
   ```

4. **使用瀏覽器開發工具**
   - 打開 Network 標籤
   - 查看實際發送的 URL
   - 檢查是否有尾隨斜線

---

## 📚 相關資源

- [RESTful 設計原則](restful-principles.md)
- [HTTP 方法使用](http-methods.md)
- [完整範例](complete-examples.md)
- FastAPI 官方文檔 (使用 context7 查詢)

---

**記住**：本專案統一使用「無尾隨斜線」標準 - 沒有例外！
