# RESTful 設計原則

## 核心概念

REST (Representational State Transfer) 是一種網路應用程式的架構風格。

### 資源導向 (Resource-Oriented)

- **資源 (Resource)**: API 操作的實體對象（用戶、檔案、配對等）
- **URI**: 資源的唯一標識符
- **HTTP 方法**: 對資源執行的操作

---

## HTTP 方法語義

| 方法 | 用途 | 冪等性 | 安全性 |
|------|------|--------|--------|
| GET | 獲取資源 | ✅ 是 | ✅ 是 |
| POST | 創建資源 | ❌ 否 | ❌ 否 |
| PUT | 完整更新資源 | ✅ 是 | ❌ 否 |
| PATCH | 部分更新資源 | ❌ 否 | ❌ 否 |
| DELETE | 刪除資源 | ✅ 是 | ❌ 否 |

---

## MergeMeet 範例

### Profile（個人檔案）
```python
GET    /api/profile           # 獲取個人檔案
POST   /api/profile           # 創建個人檔案
PUT    /api/profile           # 完整更新檔案
PATCH  /api/profile           # 部分更新檔案
```

### Photos（照片）- 子資源
```python
GET    /api/profile/photos              # 獲取所有照片
POST   /api/profile/photos              # 上傳照片
DELETE /api/profile/photos/{photo_id}   # 刪除特定照片
PUT    /api/profile/photos/{photo_id}/primary  # 設為主照片
```

### Discovery（探索配對）
```python
GET    /api/discovery/browse             # 瀏覽候選人
POST   /api/discovery/like/{user_id}     # 喜歡用戶
POST   /api/discovery/pass/{user_id}     # 跳過用戶
GET    /api/discovery/matches            # 配對列表
DELETE /api/discovery/matches/{match_id} # 取消配對
```

---

## RESTful URL 設計原則

### ✅ 好的設計

1. **使用名詞，不是動詞**
   ```python
   ✅ GET /api/profile
   ❌ GET /api/getProfile
   ```

2. **使用複數形式表示集合**
   ```python
   ✅ GET /api/profile/photos
   ❌ GET /api/profile/photo
   ```

3. **使用層級結構表示關係**
   ```python
   ✅ GET /api/messages/matches/{match_id}/messages
   ❌ GET /api/messages/getMatchMessages?matchId=123
   ```

4. **使用 HTTP 方法而非 URL 動作**
   ```python
   ✅ DELETE /api/profile/photos/{id}
   ❌ POST /api/profile/photos/delete/{id}
   ```

### ❌ 避免的設計

1. **URL 中包含動詞**
   ```python
   ❌ POST /api/profile/create
   ❌ GET /api/user/getDetails
   ```

2. **使用查詢參數做 CRUD**
   ```python
   ❌ POST /api/profile?action=delete
   ```

3. **過度嵌套**
   ```python
   ❌ GET /api/users/{id}/profile/photos/{photo_id}/comments/{comment_id}
   ```

---

## 狀態碼使用

### 成功回應
- `200 OK` - 成功獲取/更新
- `201 Created` - 成功創建
- `204 No Content` - 成功刪除（無內容返回）

### 客戶端錯誤
- `400 Bad Request` - 請求格式錯誤
- `401 Unauthorized` - 未認證
- `403 Forbidden` - 無權限
- `404 Not Found` - 資源不存在

### 伺服器錯誤
- `500 Internal Server Error` - 伺服器錯誤

---

## MergeMeet 完整範例

```python
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/discovery", tags=["Discovery"])

# ✅ RESTful 設計
@router.get("/browse", response_model=List[UserCard])
async def browse_candidates():
    """瀏覽候選人（GET 獲取資源）"""
    return candidates

@router.post("/like/{user_id}", status_code=status.HTTP_201_CREATED)
async def like_user(user_id: str):
    """喜歡用戶（POST 創建資源）"""
    # 創建 Like 記錄
    return {"liked": True}

@router.get("/matches", response_model=List[Match])
async def get_matches():
    """獲取配對列表（GET 獲取集合）"""
    return matches

@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unmatch(match_id: str):
    """取消配對（DELETE 刪除資源）"""
    # 刪除配對記錄
    return
```

---

## 查詢官方文檔

使用 context7 MCP 查詢 RESTful 最佳實踐：

```bash
context7: resolve-library-id "fastapi"
context7: get-library-docs "/fastapi" topic="REST API design" mode="info"
```

---

## 參考資源

- [狀態碼指南](status-codes.md)
- [完整範例](complete-examples.md)
