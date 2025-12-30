# RESTful 設計原則

> 本文件只記錄專案特有範例。通用 REST 知識請直接詢問 Claude。

---

## HTTP 方法速查

| 方法 | 用途 | 冪等性 |
|------|------|--------|
| GET | 獲取資源 | ✅ |
| POST | 創建資源 | ❌ |
| PUT | 完整更新 | ✅ |
| PATCH | 部分更新 | ❌ |
| DELETE | 刪除資源 | ✅ |

---

## MergeMeet API 範例

### Profile（個人檔案）

```
GET    /api/profile                        # 獲取個人檔案
PUT    /api/profile                        # 更新檔案
PUT    /api/profile/interests              # 更新興趣
POST   /api/profile/photos                 # 上傳照片
DELETE /api/profile/photos/{photo_id}      # 刪除照片
```

### Discovery（探索配對）

```
GET    /api/discovery/browse               # 瀏覽候選人
POST   /api/discovery/like/{user_id}       # 喜歡用戶
POST   /api/discovery/pass/{user_id}       # 跳過用戶
GET    /api/discovery/matches              # 配對列表
```

### Messages（訊息）

```
GET    /api/messages/conversations                  # 對話列表
GET    /api/messages/matches/{match_id}/messages    # 聊天記錄
DELETE /api/messages/messages/{message_id}          # 刪除訊息
```

### Safety（安全）

```
POST   /api/safety/block/{user_id}         # 封鎖用戶
DELETE /api/safety/block/{user_id}         # 解除封鎖
GET    /api/safety/blocked                 # 封鎖列表
POST   /api/safety/report                  # 舉報用戶
```

---

## 相關資源

- [SKILL.md](../SKILL.md) - 核心規則
