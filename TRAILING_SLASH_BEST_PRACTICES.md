# FastAPI Trailing Slash 最佳實踐指南

**適用專案**: MergeMeet
**更新日期**: 2025-11-14
**狀態**: ✅ 已實施

---

## 🎯 核心原則

> **所有 API 端點統一不使用 trailing slash**

這是 RESTful API 的業界標準，也是最簡單、最一致的方案。

---

## ✅ 正確的實施方式

### 1. FastAPI 應用配置

```python
# backend/app/main.py

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    redirect_slashes=False,  # ⭐ 重要：禁用自動重定向
)
```

**為什麼**:
- 避免 307 重定向
- 前端不會因重定向丟失 Authorization Header
- 明確的錯誤訊息 (404 而不是 307)

### 2. Router 定義模式

```python
# backend/app/api/profile.py

# ✅ 推薦：在 Router 內定義完整 prefix
router = APIRouter(prefix="/api/profile")

@router.post("")           # → /api/profile
@router.get("")            # → /api/profile
@router.put("/interests")  # → /api/profile/interests
```

```python
# backend/app/main.py

# ✅ 註冊時不需要再加 prefix
app.include_router(profile.router, tags=["個人檔案"])
```

### 3. 前端 API 調用

```javascript
// frontend/src/stores/profile.js

// ✅ 所有 API 都不使用 trailing slash
apiClient.get('/api/profile')
apiClient.post('/api/profile', data)
apiClient.put('/api/profile/interests', data)
apiClient.get('/api/profile/interest-tags')
```

---

## ❌ 常見錯誤

### 錯誤 1: 混合使用

```python
# ❌ 不要這樣做
@router.post("/")     # 這會變成 /api/profile/
@router.get("")       # 這會變成 /api/profile
```

**問題**: 不一致，前端需要記住哪些 API 帶斜線

### 錯誤 2: 依賴隱式行為

```python
# ❌ 不推薦
router = APIRouter()  # 無 prefix

# main.py
app.include_router(router, prefix="/api/profile")
```

**問題**:
- 路由定義分散在兩個地方
- 容易混淆實際的 URL
- FastAPI 可能添加隱式的 trailing slash

### 錯誤 3: 前端帶 trailing slash

```javascript
// ❌ 錯誤
apiClient.get('/api/profile/')
apiClient.post('/api/profile/', data)
```

**結果**: HTTP 404 Not Found

---

## 📋 完整的 API 規範

### Profile API
```
POST   /api/profile                    ✅
GET    /api/profile                    ✅
PATCH  /api/profile                    ✅
PUT    /api/profile/interests          ✅
POST   /api/profile/photos             ✅
DELETE /api/profile/photos/{photo_id}  ✅
GET    /api/profile/interest-tags      ✅
```

### Messages API
```
GET    /api/messages/conversations                ✅
GET    /api/messages/matches/{match_id}/messages  ✅
POST   /api/messages/messages/read                ✅
DELETE /api/messages/messages/{message_id}        ✅
```

### Discovery API
```
GET    /api/discovery/browse           ✅
POST   /api/discovery/like/{user_id}   ✅
POST   /api/discovery/pass/{user_id}   ✅
GET    /api/discovery/matches          ✅
```

---

## 🔍 快速檢查清單

新增 API 時，請檢查：

- [ ] Router 使用 `APIRouter(prefix="/api/xxx")`
- [ ] 路由定義不使用 trailing slash: `@router.get("")` 或 `@router.get("/path")`
- [ ] main.py 註冊時不重複加 prefix
- [ ] 前端調用不帶 trailing slash
- [ ] 測試腳本使用無斜線格式

---

## 🧪 測試方法

### 後端測試

```bash
# ✅ 正確 - 應該返回 200
curl -w "\nHTTP: %{http_code}\n" -X GET "http://localhost:8000/api/profile" \
  -H "Authorization: Bearer <token>"

# ❌ 錯誤 - 應該返回 404
curl -w "\nHTTP: %{http_code}\n" -X GET "http://localhost:8000/api/profile/" \
  -H "Authorization: Bearer <token>"
```

### 前端測試

開啟 Chrome DevTools > Network 標籤，檢查：
- ✅ 所有請求 URL 不帶 trailing slash
- ✅ 所有響應 HTTP 200 (不是 307)
- ✅ Console 無錯誤

---

## 📚 參考資料

### 業界標準

**GitHub API**:
```
GET /user
GET /user/repos
POST /user/repos
```

**Stripe API**:
```
GET /v1/customers
POST /v1/customers
GET /v1/customers/{id}
```

**Twitter API**:
```
GET /2/tweets
POST /2/tweets
GET /2/tweets/{id}
```

**共同點**: 全部不使用 trailing slash ✅

### FastAPI 官方文檔

- [Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/)
- [APIRouter](https://fastapi.tiangolo.com/tutorial/bigger-applications/)

---

## 💡 為什麼選擇這個方案

### 優點
1. ✅ **簡單**: 只有一種格式，無需記憶
2. ✅ **一致**: 前後端統一
3. ✅ **標準**: 符合 RESTful 最佳實踐
4. ✅ **效能**: 無重定向，更快
5. ✅ **清晰**: 明確的 404 錯誤而不是 307

### 對比其他方案

**方案 A: 全部使用 trailing slash**
- ❌ 與業界標準不符
- ❌ 前端需要記得加斜線
- ❌ URL 看起來冗余

**方案 B: 混合使用**
- ❌ 最糟糕的選擇
- ❌ 不一致，容易出錯
- ❌ 增加心智負擔

**方案 C: 統一不使用 (本方案)**
- ✅ 最佳實踐
- ✅ 簡單、一致、標準

---

## 🎓 學到的教訓

### FastAPI 的隱式行為

**問題**:
```python
router = APIRouter()
@router.post("")
```
加上 `app.include_router(router, prefix="/api/profile")` 後
實際會變成 `/api/profile/` (帶 trailing slash)

**解決**:
```python
router = APIRouter(prefix="/api/profile")
@router.post("")
```
實際路徑: `/api/profile` (無 trailing slash)

### 307 重定向的坑

**問題**:
- 瀏覽器在 307 重定向時會**丟失 Authorization Header**
- 導致認證失敗 (403 Forbidden)

**解決**:
- 設置 `redirect_slashes=False`
- 統一不使用 trailing slash

---

## ✅ 實施檢查表

### 新專案
- [ ] FastAPI 配置 `redirect_slashes=False`
- [ ] 所有 Router 在內部定義 prefix
- [ ] 文檔明確規定不使用 trailing slash
- [ ] 前端 API 客戶端配置

### 現有專案 (重構)
- [ ] 審查所有 Router 定義
- [ ] 統一 prefix 位置 (Router 內或 main.py)
- [ ] 更新測試腳本
- [ ] 更新前端 API 調用
- [ ] 執行完整測試

---

**總結**: 簡單即美，統一不用斜線！ 🎯
