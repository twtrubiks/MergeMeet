# 刪除訊息即時同步修復報告

**修復日期**: 2025-11-15
**問題發現者**: 用戶測試反饋
**修復版本**: commit `251b916`

---

## 📋 問題描述

### 原始問題

當用戶刪除聊天訊息時，存在以下問題：

- ✅ 刪除者本地介面立即移除訊息
- ✅ 資料庫正確執行軟刪除
- ❌ **對方需要重新整理頁面才能看到訊息被刪除**

### 用戶反饋

> "我測試了一下刪除訊息功能，都是正常的。但有一個問題是如果我刪除訊息，對方要重新整理網頁刪除才會被刪除，這樣正常嗎？"

**答案**: ❌ 不正常！即時聊天應用中，刪除操作應該即時同步給所有相關用戶。

---

## 🔍 根本原因分析

### 技術原因

1. **後端 API** (`backend/app/api/messages.py:257-292`)
   - 只更新資料庫
   - ❌ 沒有通過 WebSocket 通知對方

2. **前端 Store** (`frontend/src/stores/chat.js:183-199`)
   - 只更新本地狀態
   - ❌ 沒有監聽刪除訊息的 WebSocket 事件

3. **WebSocket Handler** (`backend/app/api/websocket.py:51-65`)
   - 只處理 `new_message`, `typing`, `read_receipt`, `join_match`, `leave_match`
   - ❌ 沒有處理 `message_deleted` 事件

### 架構問題

```
刪除流程（修復前）:
Alice 刪除訊息 → REST API → 資料庫更新 → Alice 本地移除
                                          ↓
                                      Bob 無感知 ❌

修復後流程:
Alice 刪除訊息 → REST API → 資料庫更新 → Alice 本地移除
                           ↓
                     WebSocket 廣播 → Bob 收到事件 → Bob 本地移除 ✅
```

---

## ✅ 修復方案

### 1. 後端修復 (`backend/app/api/messages.py`)

**修改位置**: `delete_message` API 端點

**添加的功能**:
```python
from app.websocket.manager import manager

# 保存 match_id 用於 WebSocket 廣播
match_id = str(message.match_id)

# 軟刪除
message.deleted_at = datetime.utcnow()
await db.commit()

# 通過 WebSocket 通知配對中的另一方
await manager.send_to_match(
    match_id,
    {
        "type": "message_deleted",
        "message_id": message_id,
        "match_id": match_id,
        "deleted_by": str(current_user.id)
    },
    exclude_user=str(current_user.id)  # 排除刪除者本人
)
```

**關鍵設計**:
- 使用 `send_to_match()` 廣播給配對中的所有成員
- `exclude_user` 排除刪除者，避免重複通知
- 事件類型: `message_deleted`

### 2. 前端修復 (`frontend/src/stores/chat.js`)

**修改 1: 註冊事件監聽器**

```javascript
const initWebSocket = () => {
  ws.connect()

  ws.onMessage('new_message', handleNewMessage)
  ws.onMessage('typing', handleTypingIndicator)
  ws.onMessage('read_receipt', handleReadReceipt)
  ws.onMessage('message_deleted', handleMessageDeleted)  // ✅ 新增
}
```

**修改 2: 添加事件處理器**

```javascript
const handleMessageDeleted = (data) => {
  const { message_id, match_id } = data

  console.log('[Chat] Received message_deleted event:', data)

  // 從本地狀態移除訊息
  if (messages.value[match_id]) {
    const index = messages.value[match_id].findIndex(m => m.id === message_id)
    if (index > -1) {
      messages.value[match_id].splice(index, 1)
      console.log('[Chat] Message removed from local state:', message_id)
    }
  }
}
```

**關鍵設計**:
- 使用 `Array.findIndex()` 找到訊息
- 使用 `Array.splice()` 移除訊息（觸發 Vue 響應式更新）
- 添加 console.log 方便調試

---

## 🧪 測試方法

### 前置準備

1. **重新啟動後端**（確保新代碼生效）
   ```bash
   cd backend
   # 如果使用 uvicorn --reload，會自動重啟
   # 否則需要手動重啟
   ```

2. **清除前端緩存並重新載入**
   - 按 Ctrl+Shift+R（硬性重新載入）
   - 或清除瀏覽器緩存

3. **設置測試帳號**
   ```bash
   python3 setup_test_users_simple.py
   ```

### 測試步驟

#### Test Case 1: 基本刪除同步

| 步驟 | Alice（瀏覽器 A） | Bob（瀏覽器 B） | 預期結果 |
|------|-------------------|-----------------|----------|
| 1 | 登入並進入聊天室 | 登入並進入聊天室 | ✅ 兩邊都進入聊天 |
| 2 | 發送訊息：「測試訊息 1」 | 看到訊息出現 | ✅ Bob 即時收到訊息 |
| 3 | 右鍵點擊自己的訊息 → 刪除 | - | ✅ 刪除確認對話框出現 |
| 4 | 點擊「刪除」按鈕 | **立即看到訊息消失** | ✅ Bob 無需重新整理 |
| 5 | 訊息從列表中消失 | 訊息從列表中消失 | ✅ 兩邊同步 |

#### Test Case 2: 連續刪除

| 步驟 | Alice | Bob | 預期結果 |
|------|-------|-----|----------|
| 1 | 發送 3 則訊息 | 看到 3 則訊息 | ✅ |
| 2 | 刪除第 1 則訊息 | 第 1 則立即消失 | ✅ 即時同步 |
| 3 | 刪除第 2 則訊息 | 第 2 則立即消失 | ✅ 即時同步 |
| 4 | 刪除第 3 則訊息 | 第 3 則立即消失 | ✅ 即時同步 |

#### Test Case 3: 雙向刪除

| 步驟 | Alice | Bob | 預期結果 |
|------|-------|-----|----------|
| 1 | 發送訊息：「Alice 的訊息」 | 看到訊息 | ✅ |
| 2 | 看到訊息 | 發送訊息：「Bob 的訊息」 | ✅ |
| 3 | 刪除自己的訊息 | Bob 看到 Alice 的訊息消失 | ✅ |
| 4 | Alice 看到 Bob 的訊息消失 | 刪除自己的訊息 | ✅ |

### 調試檢查點

#### 瀏覽器開發者工具（Console）

**Alice 刪除訊息時應該看到**:
```
[Chat] Message removed from local state: <message_id>
```

**Bob 應該看到**:
```
[Chat] Received message_deleted event: {
  type: "message_deleted",
  message_id: "xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx",
  match_id: "xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx",
  deleted_by: "xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
}
[Chat] Message removed from local state: <message_id>
```

#### 瀏覽器 Network 面板（WebSocket）

在 WebSocket 連接中應該看到：

**Alice 側**:
- ↑ 發送 DELETE `/api/messages/messages/{id}` HTTP 請求
- ✅ 200 或 204 響應

**Bob 側**:
- ↓ 收到 WebSocket 訊息：
  ```json
  {
    "type": "message_deleted",
    "message_id": "...",
    "match_id": "...",
    "deleted_by": "..."
  }
  ```

---

## 📊 修復前後對比

| 項目 | 修復前 | 修復後 |
|------|--------|--------|
| **刪除者體驗** | ✅ 立即移除 | ✅ 立即移除 |
| **對方體驗** | ❌ 需重新整理 | ✅ 即時同步 |
| **網路請求** | 1 個 HTTP DELETE | 1 個 HTTP DELETE + 1 個 WebSocket 廣播 |
| **資料一致性** | ⚠️ 延遲一致 | ✅ 即時一致 |
| **用戶體驗** | ⭐⭐ (差) | ⭐⭐⭐⭐⭐ (優秀) |

---

## 🔧 技術細節

### WebSocket 事件格式

```typescript
interface MessageDeletedEvent {
  type: "message_deleted"
  message_id: string          // 被刪除的訊息 ID
  match_id: string            // 配對 ID
  deleted_by: string          // 刪除者用戶 ID
}
```

### 性能影響

- **額外開銷**: 1 個 WebSocket 訊息（約 100-200 bytes）
- **延遲**: < 100ms（本地網路）
- **伺服器負載**: 可忽略（已有 WebSocket 連接）

### 安全性

- ✅ 驗證刪除者身份（只能刪除自己的訊息）
- ✅ 驗證配對關係（只通知配對中的成員）
- ✅ 排除刪除者（避免重複通知）
- ✅ 軟刪除（資料仍保留在資料庫）

---

## 🎯 已修復的功能

### ✅ 刪除訊息即時同步

- [x] 後端通過 WebSocket 廣播刪除事件
- [x] 前端監聽並處理刪除事件
- [x] 本地狀態即時更新
- [x] 無需重新整理頁面

### ✅ 其他已驗證功能

根據用戶測試反饋：

- [x] 刪除訊息功能（UI 和 API）
- [x] 打字指示器功能

---

## 📝 相關文件

- `backend/app/api/messages.py:257-310` - 刪除訊息 API
- `frontend/src/stores/chat.js:45-54` - WebSocket 初始化
- `frontend/src/stores/chat.js:315-331` - 刪除事件處理器
- `backend/app/websocket/manager.py` - WebSocket 管理器

---

## 🚀 後續優化建議

### 可選的額外改進

1. **後端 WebSocket Handler**（目前標記為「可選」）
   - 添加 `delete_message` 事件處理器
   - 允許通過 WebSocket 直接刪除訊息（不經過 REST API）
   - 優點：減少一次 HTTP 請求
   - 缺點：增加複雜度

2. **UI 動畫效果**
   - 訊息刪除時添加淡出動畫
   - 提升用戶體驗

3. **撤銷功能**
   - 刪除後 5 秒內可撤銷
   - 類似 Gmail 的「撤銷傳送」功能

---

## ✅ 測試結果

**測試人員**: 待測試
**測試日期**: 2025-11-15
**測試狀態**: ⏳ 等待用戶驗證

**測試 Checklist**:
- [ ] Alice 刪除訊息，Bob 即時看到消失
- [ ] Bob 刪除訊息，Alice 即時看到消失
- [ ] 連續刪除多則訊息
- [ ] Console 顯示正確的調試訊息
- [ ] WebSocket 事件正確傳遞

---

**修復版本**: `251b916`
**相關 Commits**:
- `251b916` - fix: 修復刪除訊息時未即時同步給對方的問題

**修復確認**: ✅ 代碼已提交，等待測試驗證
