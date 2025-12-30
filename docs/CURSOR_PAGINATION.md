# Cursor-based Pagination 技術說明

## 概述

MergeMeet 的聊天訊息 API 使用 **Cursor-based Pagination**（游標分頁），這是聊天應用的業界標準做法。

Slack、Discord 等主流聊天應用的 API 都採用類似的 cursor-based 分頁機制。

## 為什麼選擇 Cursor-based Pagination？

### Offset-based vs Cursor-based 比較

| 比較項目 | Offset-based | Cursor-based |
|---------|--------------|--------------|
| 新資料插入 | 會導致資料重複或遺漏 | 不受影響 |
| 效能 | 大 offset 時效能差 (O(n)) | 使用索引，效能穩定 (O(1)) |
| 即時場景 | 不適合聊天等即時應用 | 專為即時場景設計 |
| 實現複雜度 | 簡單 | 稍複雜 |

### 為什麼 Offset-based 在聊天場景有問題？

假設有 100 條訊息，每頁顯示 10 條：

```
原始狀態：
Page 1: [91-100]  ← 用戶正在看
Page 2: [81-90]

此時對方發送新訊息（ID 101）

新狀態：
Page 1: [92-101]
Page 2: [82-91]  ← 用戶載入 Page 2，訊息 91 重複了！
```

Cursor-based 則不會有這個問題：
```
before_id=91 → 取 ID < 91 的訊息 → [81-90]
無論有多少新訊息插入，結果都是正確的
```

## API 使用方式

### 端點

```
GET /api/messages/matches/{match_id}/messages
```

### 查詢參數

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| `before_id` | UUID | 否 | null | Cursor: 載入比此訊息 ID 更早的訊息 |
| `limit` | int | 否 | 50 | 每次載入數量（1-100）|

### 回應格式

```json
{
  "messages": [
    {
      "id": "uuid",
      "match_id": "uuid",
      "sender_id": "uuid",
      "content": "Hello!",
      "message_type": "TEXT",
      "is_read": "2025-12-10T10:00:00Z",
      "sent_at": "2025-12-10T09:55:00Z"
    }
  ],
  "has_more": true,
  "next_cursor": "uuid-of-oldest-message",
  "total": 150
}
```

### 欄位說明

- `messages`: 訊息列表，按時間正序排列（舊的在前，新的在後）
- `has_more`: 是否還有更早的訊息
- `next_cursor`: 本次結果中最舊訊息的 ID，供下次查詢使用
- `total`: 總訊息數（供 UI 顯示，如「共 150 則訊息」）

## 使用流程

### 1. 初次載入（進入聊天室）

不傳 `before_id`，取最新 N 條訊息：

```javascript
// 前端
const result = await api.get('/messages/matches/{matchId}/messages')
// result: { messages: [...最新50條], has_more: true, next_cursor: "uuid", total: 150 }
```

```bash
# curl 測試
curl -X GET "http://localhost:8000/api/messages/matches/{match_id}/messages" \
  -H "Authorization: Bearer {token}"
```

### 2. 載入更多（向上滾動）

傳入 `before_id`（上次的 `next_cursor`），取更早的訊息：

```javascript
// 前端
const result = await api.get('/messages/matches/{matchId}/messages', {
  params: { before_id: nextCursor }
})
// result: { messages: [...更早的訊息], has_more: false, next_cursor: null, total: 150 }
```

```bash
# curl 測試
curl -X GET "http://localhost:8000/api/messages/matches/{match_id}/messages?before_id={cursor}" \
  -H "Authorization: Bearer {token}"
```

### 3. 判斷是否還有更多

當 `has_more` 為 `false` 時，表示已載入所有歷史訊息。

## 前端實現範例

### Store (Pinia)

```javascript
const fetchChatHistory = async (matchId, beforeId = null, limit = 50) => {
  const params = { limit }
  if (beforeId) {
    params.before_id = beforeId
  }

  const response = await apiClient.get(`/messages/matches/${matchId}/messages`, { params })

  if (beforeId) {
    // 載入更多：將歷史訊息插入到開頭
    messages.value[matchId] = [
      ...response.data.messages,
      ...messages.value[matchId]
    ]
  } else {
    // 初次載入：直接覆蓋
    messages.value[matchId] = response.data.messages
  }

  return response.data
}
```

### 頁面 (Vue)

```javascript
// 狀態
const nextCursor = ref(null)
const hasMore = ref(true)

// 初次載入
onMounted(async () => {
  const result = await chatStore.fetchChatHistory(matchId)
  hasMore.value = result.has_more
  nextCursor.value = result.next_cursor
})

// 載入更多（滾動到頂部時觸發）
const loadMoreMessages = async () => {
  if (!hasMore.value || !nextCursor.value) return

  const result = await chatStore.fetchChatHistory(matchId, nextCursor.value)
  hasMore.value = result.has_more
  nextCursor.value = result.next_cursor
}
```

## 後端實現要點

### 1. 查詢邏輯

```python
# 構建查詢條件
conditions = [
    Message.match_id == match_id,
    Message.deleted_at.is_(None)
]

# 如果有 cursor，添加 before 條件
if before_id:
    cursor_sent_at = get_message_sent_at(before_id)
    if cursor_sent_at:
        # 處理相同時間戳的訊息
        conditions.append(
            or_(
                Message.sent_at < cursor_sent_at,
                and_(
                    Message.sent_at == cursor_sent_at,
                    Message.id < before_id
                )
            )
        )

# 倒序取 limit+1 條（多取一條判斷 has_more）
query = (
    select(Message)
    .where(and_(*conditions))
    .order_by(desc(Message.sent_at), desc(Message.id))
    .limit(limit + 1)
)
```

### 2. 處理結果

```python
# 判斷是否有更多
has_more = len(messages) > limit
if has_more:
    messages = messages[:limit]

# 反轉為正序（前端期望舊的在前）
messages = list(reversed(messages))

# 計算 next_cursor
next_cursor = messages[0].id if messages and has_more else None
```

## 注意事項

1. **索引優化**：確保 `(match_id, sent_at)` 有複合索引，提升查詢效能
2. **相同時間戳**：使用 `(sent_at, id)` 組合排序，處理同一秒發送的多條訊息
3. **刪除訊息**：軟刪除不影響 cursor，因為使用 `sent_at` 而非 `id` 排序

## 相關檔案

- 後端 API: `backend/app/api/messages.py`
- 後端 Schema: `backend/app/schemas/message.py`
- 前端 Store: `frontend/src/stores/chat.js`
- 前端頁面: `frontend/src/views/Chat.vue`
- 測試: `backend/tests/test_messages.py`
