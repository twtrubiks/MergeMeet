# HTTP 狀態碼指南

## 常用狀態碼

### 2xx 成功
- **200 OK** - GET/PUT/PATCH 成功
- **201 Created** - POST 創建成功
- **204 No Content** - DELETE 成功（無回傳內容）

### 4xx 客戶端錯誤
- **400 Bad Request** - 請求格式錯誤、驗證失敗
- **401 Unauthorized** - 未認證（缺少或無效的 Token）
- **403 Forbidden** - 無權限訪問
- **404 Not Found** - 資源不存在或 **URL 有尾隨斜線** ⚠️

### 5xx 伺服器錯誤
- **500 Internal Server Error** - 伺服器錯誤

---

## MergeMeet 使用範例

```python
from fastapi import status

# 成功創建
@router.post("/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo():
    return {"photo_id": "123"}

# 成功刪除（無內容）
@router.delete("/photos/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(id: str):
    return  # 不返回任何內容

# 錯誤處理
@router.get("", response_model=ProfileResponse)
async def get_profile():
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在"
        )
    return profile

# 驗證錯誤
if len(interests) > 10:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="興趣標籤最多 10 個"
    )
```

---

## 查詢官方文檔

```bash
context7: resolve-library-id "fastapi"
context7: get-library-docs "/fastapi" topic="status codes"
```
