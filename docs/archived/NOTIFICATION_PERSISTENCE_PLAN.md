# 通知持久化功能規劃

> **狀態**: ✅ 已完成
> **優先級**: 中
> **實作日期**: 2025-12-14
> **實際工時**: ~2 小時
> **實作方式**: TDD (測試驅動開發)

---

## 背景

目前系統有兩種「未讀」機制：

| 項目 | ChatList 未讀數 | 鈴鐺通知 |
|------|----------------|---------|
| 位置 | 對話列表頭像右上角 | NavBar 右上角鈴鐺 |
| 資料來源 | 後端 API（`unread_count` 欄位） | 前端記憶體 |
| 重整後 | ✅ 保留 | ❌ 消失 |

**問題**：鈴鐺通知在頁面重新整理後會消失，因為只存在前端記憶體中。

---

## 目標

讓鈴鐺通知也能持久化，頁面重整後仍能顯示未讀通知。

---

## 資料表設計

### notifications 表

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,  -- notification_message, notification_match, notification_liked
    title VARCHAR(200) NOT NULL,
    content TEXT,
    data JSONB,  -- 額外資料：match_id, sender_id, sender_name 等
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 索引
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 索引優化
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_user_created ON notifications(user_id, created_at DESC);
```

### SQLAlchemy Model

```python
# app/models/notification.py

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone


class Notification(Base):
    """通知模型 - 持久化用戶通知"""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 通知類型：notification_message, notification_match, notification_liked
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text)

    # 額外資料（JSON 格式）
    # - notification_message: { match_id, sender_id, sender_name, preview }
    # - notification_match: { match_id, matched_user_id, matched_user_name, matched_user_avatar }
    # - notification_liked: {} (保持神秘感，不透露是誰)
    data = Column(JSONB, default=dict)

    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # 關聯
    user = relationship("User", back_populates="notifications")
```

---

## API 設計

### 端點列表

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/notifications` | 取得通知列表（分頁） |
| GET | `/api/notifications/unread-count` | 取得未讀數量 |
| PUT | `/api/notifications/{id}/read` | 標記單個為已讀 |
| PUT | `/api/notifications/read-all` | 標記全部已讀 |
| DELETE | `/api/notifications/{id}` | 刪除單個通知 |

### API 詳細規格

#### 1. 取得通知列表

```
GET /api/notifications?limit=20&offset=0&unread_only=false
```

**Response:**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "type": "notification_message",
      "title": "Bob 發送了訊息",
      "content": "你好嗎？",
      "data": {
        "match_id": "uuid",
        "sender_id": "uuid",
        "sender_name": "Bob"
      },
      "is_read": false,
      "created_at": "2025-12-12T00:00:00Z"
    }
  ],
  "total": 15,
  "unread_count": 3
}
```

#### 2. 取得未讀數量

```
GET /api/notifications/unread-count
```

**Response:**
```json
{
  "unread_count": 3
}
```

#### 3. 標記為已讀

```
PUT /api/notifications/{id}/read
PUT /api/notifications/read-all
```

**Response:**
```json
{
  "success": true
}
```

---

## 實作步驟

### Phase 1: 後端 ✅

#### 1.1 新增 Model（新增檔案）
- [x] 建立 `app/models/notification.py`
- [x] 在 `app/models/__init__.py` 匯出 Notification
- [x] 在 `User` model 新增 `notifications` relationship

#### 1.2 資料庫遷移
- [x] 執行 `alembic revision --autogenerate -m "add notifications table"`
- [x] 執行 `alembic upgrade head`

#### 1.3 新增 API（新增檔案）
- [x] 建立 `app/api/notifications.py`
- [x] 實作 5 個端點
- [x] 在 `app/main.py` 註冊路由

#### 1.4 修改 WebSocket 通知發送
- [x] `app/api/discovery.py` - 發送 `notification_match` / `notification_liked` 時寫入 DB
- [x] `app/api/websocket.py` - 發送 `notification_message` 時寫入 DB

### Phase 2: 前端 ✅

#### 2.1 修改 Notification Store
- [x] 新增 `fetchNotifications()` 方法
- [x] 新增 `fetchUnreadCount()` 方法
- [x] 新增 `markAsReadAPI()` 方法（呼叫後端 API）
- [x] 新增 `markAllAsReadAPI()` 方法
- [x] 新增 `deleteNotificationAPI()` 方法

#### 2.2 修改 App.vue
- [x] 在 `onMounted` 時呼叫 `fetchNotifications()`
- [x] 監聽登入狀態，登入時載入通知

#### 2.3 修改 NotificationBell.vue
- [x] 點擊「全部已讀」時呼叫後端 API
- [x] 點擊單個通知時呼叫後端 API 標記已讀

---

## 檔案變更清單

### 新增檔案

| 檔案 | 說明 |
|------|------|
| `backend/app/models/notification.py` | Notification Model (~40 行) |
| `backend/app/api/notifications.py` | 通知 API (~100 行) |
| `backend/alembic/versions/xxx_add_notifications.py` | 資料庫遷移 |

### 修改檔案

| 檔案 | 改動量 | 說明 |
|------|--------|------|
| `backend/app/models/__init__.py` | 2 行 | 匯出 Notification |
| `backend/app/models/user.py` | 3 行 | 新增 relationship |
| `backend/app/api/__init__.py` | 2 行 | 註冊路由 |
| `backend/app/api/discovery.py` | 10 行 | 寫入 DB |
| `backend/app/api/websocket.py` | 10 行 | 寫入 DB |
| `frontend/src/stores/notification.js` | 30 行 | 新增 API 呼叫 |
| `frontend/src/App.vue` | 5 行 | 初始化時取得通知 |

---

## 注意事項

1. **API URL 無尾隨斜線** - 遵循專案規範
2. **非同步處理** - 後端全部使用 `async/await`
3. **通知去重** - 避免重複建立相同通知
4. **效能考量** - 使用索引優化查詢，限制返回數量
5. **清理機制** - 考慮定期清理 30 天以上的已讀通知（可選）

---

## 測試計畫

### 後端測試 ✅ (17 個測試案例)
- [x] 建立通知 API 測試
- [x] 取得通知列表測試
- [x] 標記已讀測試
- [x] WebSocket 發送時自動建立通知測試

**測試檔案**: `backend/tests/test_notification_persistence.py`

```python
# 測試類別
class TestNotificationModel:     # 5 個測試
class TestNotificationAPI:       # 10 個測試
class TestNotificationAutoCreate: # 2 個測試
```

### 前端測試（手動驗證）✅
- [x] 頁面載入時取得通知
- [x] 重整後通知保留
- [x] 即時通知 + 持久化同時運作

---

## 未來擴展（可選）

1. **推播通知** - 整合 Web Push API
2. **通知設定** - 讓用戶選擇接收哪些通知
3. **批量操作** - 批量刪除、批量已讀
4. **通知分類** - 按類型篩選通知
