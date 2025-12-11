---
name: api-routing-standards
description: FastAPI URL 標準與 RESTful 最佳實踐。本專案統一使用「無尾隨斜線」標準，違反此規則會導致 404 錯誤。涵蓋路由定義、HTTP 方法、狀態碼、CORS 配置等。當創建或修改 API 路由時自動觸發。
---

# API 路由規範 (API Routing Standards)

## ⚠️ 目的

防止常見的 404 錯誤，確保 FastAPI 路由遵循 RESTful 標準與專案規範。

**本 skill 為 GUARDRAIL 等級** - 編輯 API 路由時會強制提示，因為錯誤的 URL 格式會直接導致 404 錯誤！

---

## 🚨 最重要的規則：無尾隨斜線 (No Trailing Slash)

### 統一標準

本專案**所有 API 端點一律不使用尾隨斜線**，符合 RESTful API 業界標準。

```python
# ✅ 正確 - 無尾隨斜線
@router.get("")                          # GET /api/profile
@router.post("")                         # POST /api/profile
@router.put("/interests")                # PUT /api/profile/interests
@router.get("/browse")                   # GET /api/discovery/browse
@router.post("/like/{user_id}")          # POST /api/discovery/like/{id}

# ❌ 錯誤 - 有尾隨斜線（會導致前端 404）
@router.post("/")                        # ❌ 404 錯誤
@router.put("/interests/")               # ❌ 404 錯誤
@router.post("/like/{user_id}/")         # ❌ 404 錯誤
```

### 為什麼這麼重要？

FastAPI 配置為 `redirect_slashes=False`：

```python
# backend/app/main.py
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    redirect_slashes=False,  # 禁用自動重定向
)
```

這意味著：
- ✅ `/api/profile` → HTTP 200 (正確)
- ❌ `/api/profile/` → HTTP 404 (錯誤)
- **不會自動重定向** - Authorization Header 會在重定向中丟失

---

## 📚 何時使用此 Skill

**自動觸發時機**:
- 創建或修改 `backend/app/api/**/*.py` 中的路由
- 程式碼包含 `@router.` 或 `APIRouter`
- 關鍵字: "route", "endpoint", "API", "路由"
- 修復 404 錯誤

**手動使用**:
```bash
# Claude Code 中
使用 Skill: api-routing-standards
```

---

## 🎯 快速檢查清單

創建或修改 API 路由時：

- [ ] **無尾隨斜線**: 所有路由定義不使用 `/`
- [ ] **HTTP 方法正確**: GET (讀取), POST (創建), PUT/PATCH (更新), DELETE (刪除)
- [ ] **路徑參數**: `{user_id}` 格式，不是 `<user_id>`
- [ ] **狀態碼**: 200 (成功), 201 (創建), 400 (錯誤請求), 404 (未找到)
- [ ] **回應模型**: 使用 Pydantic `response_model`
- [ ] **錯誤處理**: 使用 `HTTPException`
- [ ] **前端對應**: 確保前端 axios 也無尾隨斜線

---

## 📖 資源檔案導覽

| 需要... | 閱讀此檔案 |
|--------|----------|
| **尾隨斜線規則** (最重要) | [trailing-slash-rules.md](resources/trailing-slash-rules.md) |
| RESTful 設計原則 | [restful-principles.md](resources/restful-principles.md) |
| HTTP 方法使用 | [http-methods.md](resources/http-methods.md) |
| 路徑參數與查詢參數 | [path-parameters.md](resources/path-parameters.md) |
| 狀態碼指南 | [status-codes.md](resources/status-codes.md) |
| CORS 配置 | [cors-configuration.md](resources/cors-configuration.md) |
| 命名規範 | [naming-conventions.md](resources/naming-conventions.md) |
| 錯誤回應格式 | [error-responses.md](resources/error-responses.md) |
| 完整範例 | [complete-examples.md](resources/complete-examples.md) |

---

## 🔍 查詢官方文檔 (使用 Context7 MCP)

需要查詢 FastAPI 官方文檔時，使用 **context7 MCP**：

```bash
# 查詢 FastAPI 路由相關文檔
context7: resolve-library-id "fastapi"
context7: get-library-docs "/fastapi" topic="routing"

# 查詢 Pydantic 驗證
context7: resolve-library-id "pydantic"
context7: get-library-docs "/pydantic" topic="validation"

# 查詢 SQLAlchemy
context7: resolve-library-id "sqlalchemy"
context7: get-library-docs "/sqlalchemy" topic="async"
```

**常用查詢**:
- `topic="routing"` - 路由定義
- `topic="path parameters"` - 路徑參數
- `topic="response model"` - 回應模型
- `topic="status codes"` - 狀態碼
- `mode="info"` - 概念性文檔
- `mode="code"` - 程式碼範例

---

## ✅ 正確範例

### Profile API
```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """獲取個人檔案"""
    profile = await db.get(Profile, current_user.profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在"
        )
    return profile

@router.put("/interests", response_model=ProfileResponse)
async def update_interests(
    interests: List[str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新興趣標籤"""
    # 業務邏輯...
    return updated_profile

@router.post("/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    """上傳照片"""
    # 檔案處理...
    return {"photo_id": photo.id}

@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """刪除照片"""
    # 刪除邏輯...
    return
```

### 前端對應 (Axios)
```javascript
// ✅ 正確 - 無尾隨斜線
await axios.get('/api/profile')
await axios.put('/api/profile/interests', { interests })
await axios.post('/api/profile/photos', formData)
await axios.delete(`/api/profile/photos/${photoId}`)

// ❌ 錯誤 - 有尾隨斜線（404）
await axios.get('/api/profile/')           // ❌
await axios.put('/api/profile/interests/', data)  // ❌
```

---

## ❌ 常見錯誤

### 錯誤 1: 使用尾隨斜線
```python
# ❌ 錯誤
@router.post("/")  # 這會導致前端 404
@router.get("/browse/")  # 這也會導致 404

# ✅ 正確
@router.post("")
@router.get("/browse")
```

### 錯誤 2: 前端和後端不一致
```python
# 後端
@router.get("/interests")  # 無斜線

# 前端 ❌
await axios.get('/api/profile/interests/')  # 有斜線 → 404

# 前端 ✅
await axios.get('/api/profile/interests')  # 無斜線 → 200
```

### 錯誤 3: 錯誤的 HTTP 方法
```python
# ❌ 錯誤 - 讀取資料應該用 GET
@router.post("/browse")  # 瀏覽應該用 GET

# ✅ 正確
@router.get("/browse")
```

---

## 🧪 測試路由

### 使用 curl 測試
```bash
# 測試時檢查 HTTP 狀態碼
curl -w "\nHTTP: %{http_code}\n" \
  -X GET "http://localhost:8000/api/profile" \
  -H "Authorization: Bearer $TOKEN"

# HTTP: 200 ✅ 正確
# HTTP: 404 ❌ URL 格式錯誤
```

### 使用 pytest 測試
```python
async def test_get_profile():
    """測試獲取個人檔案"""
    response = await client.get("/api/profile")
    assert response.status_code == 200

    # ❌ 測試不應該通過
    response = await client.get("/api/profile/")
    assert response.status_code == 404  # 有斜線會 404
```

### 使用 Swagger UI
訪問 `http://localhost:8000/docs` 查看所有端點：
- 確認所有 URL 都無尾隨斜線
- 測試端點功能
- 查看請求/回應格式

---

## 🔗 相關 Skills

- **backend-dev-fastapi** - FastAPI 完整開發指南
- **database-planning** - 資料模型設計
- **testing-guide** - API 測試策略

---

## 📝 核心原則

1. **統一無尾隨斜線** - 所有端點不使用 `/` 結尾
2. **RESTful 標準** - GET (讀), POST (創建), PUT/PATCH (更新), DELETE (刪除)
3. **明確狀態碼** - 200, 201, 400, 404, 500
4. **前後端一致** - 前端 URL 必須與後端完全匹配
5. **完整錯誤處理** - 使用 `HTTPException`
6. **Pydantic 驗證** - 使用 `response_model`

---

**Skill 狀態**: ✅ COMPLETE
**強制等級**: 🚨 BLOCK (Guardrail)
**優先級**: CRITICAL
**行數**: < 300 行 ✅
