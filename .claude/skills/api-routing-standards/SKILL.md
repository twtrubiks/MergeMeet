---
name: api-routing-standards
description: 在 MergeMeet 專案中建立或修改 API 路由時使用此 skill。它強制執行「禁止尾隨斜線」標準以防止 404 錯誤。適用於處理 FastAPI 路由、修復 404 錯誤或審查 API 端點定義時。
---

# API 路由標準

## 目的

透過確保所有 FastAPI 路由遵循專案的「無尾隨斜線」慣例，防止常見的 404 錯誤。

---

## 重要規則：禁止尾隨斜線

本專案中所有 API 端點必須不使用尾隨斜線。這是由 FastAPI 配置強制執行的。

### 正確範例

```python
# 後端路由 - 無尾隨斜線
@router.get("")                      # GET /api/profile
@router.post("")                     # POST /api/profile
@router.put("/interests")            # PUT /api/profile/interests
@router.get("/browse")               # GET /api/discovery/browse
@router.post("/like/{user_id}")      # POST /api/discovery/like/{id}
```

```javascript
// 前端 axios 呼叫 - 無尾隨斜線
await axios.get('/api/profile')
await axios.put('/api/profile/interests', data)
await axios.post('/api/profile/photos', formData)
```

### 錯誤範例（會導致 404）

```python
# 這些會導致 404 錯誤
@router.post("/")                    # 404
@router.put("/interests/")           # 404
@router.post("/like/{user_id}/")     # 404
```

```javascript
// 這些會導致 404 錯誤
await axios.get('/api/profile/')     // 404
await axios.put('/api/profile/interests/', data)  // 404
```

---

## 為什麼這很重要

FastAPI 應用程式配置了 `redirect_slashes=False`：

```python
# backend/app/main.py
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    redirect_slashes=False,  # 不自動重定向
)
```

這意味著：
- `/api/profile` 返回 HTTP 200（正確）
- `/api/profile/` 返回 HTTP 404（錯誤）
- Authorization headers 在重定向時會丟失

---

## 快速檢查清單

創建或修改 API 路由時：

- [ ] 路由定義無尾隨斜線
- [ ] HTTP 方法正確（GET/POST/PUT/PATCH/DELETE）
- [ ] 路徑參數使用 `{param}` 格式
- [ ] 回應模型使用 `response_model` 定義
- [ ] 錯誤處理使用 `HTTPException`
- [ ] 前端 axios 呼叫與後端路由完全匹配

---

## 參考資料

詳細資訊請參考以下參考文件：

| 主題 | 檔案 |
|------|------|
| 尾隨斜線規則 | [trailing-slash-rules.md](references/trailing-slash-rules.md) |
| RESTful 原則 | [restful-principles.md](references/restful-principles.md) |
| HTTP 狀態碼 | [status-codes.md](references/status-codes.md) |
| 完整範例 | [complete-examples.md](references/complete-examples.md) |

---

## 相關 Skills

- **backend-dev-fastapi** - FastAPI 開發指南
- **frontend-dev-vue3** - Vue 3 開發指南
