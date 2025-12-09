# 聊天功能除錯指南

**問題**: 打字指示器和已讀回條沒有顯示
**日期**: 2025-12-09

---

## 🔍 功能實現確認

### ✅ 已實現的功能

#### 1. 打字指示器

**前端顯示**:
- 位置：`frontend/src/views/Chat.vue:21-23`
- 條件：`v-if="chatStore.isTyping"`
- UI：顯示「正在輸入...」

**前端發送**:
- 位置：`frontend/src/views/Chat.vue:81`
- 觸發：`@input="handleTyping"`
- 邏輯：`frontend/src/views/Chat.vue:274-290`

**前端接收**:
- 位置：`frontend/src/stores/chat.js:285-308`
- 處理器：`handleTypingIndicator(data)`
- 狀態更新：`typingUsers.value[match_id] = user_id`

**後端處理**:
- 位置：`backend/app/api/websocket.py:317-342`
- 廣播：`manager.send_to_match(..., exclude_user=user_id)`

#### 2. 已讀回條

**前端顯示**:
- 位置：`frontend/src/components/chat/MessageBubble.vue:54-59`
- 條件：`v-if="isOwn && message.is_read"`
- UI：顯示「✓✓ 已讀」或「✓ 已送達」

**前端發送**:
- 位置：`frontend/src/stores/chat.js:142-160`
- 觸發：進入聊天室時自動標記
- API：`POST /messages/messages/read`
- WebSocket：`ws.sendReadReceipt(msgId)`

**後端處理**:
- 位置：`backend/app/api/websocket.py:345-391`
- 更新：`message.is_read = func.now()`
- 通知：`manager.send_personal_message(sender_id, ...)`

---

## 🐛 可能的問題

### 問題 1：WebSocket 認證後訊息處理器失效

**檢查點**:
```javascript
// frontend/src/composables/useWebSocket.js:98-100
// 認證成功後切換訊息處理器
socket.value.onmessage = normalMessageHandler
```

**可能原因**:
- onMessage 註冊的處理器在認證前註冊
- 認證後切換 onmessage 時處理器丟失

**解決方案**: 確保 onMessage 在 auth_success 後仍然有效

---

### 問題 2：沒有加入聊天室（match_rooms）

**檢查點**:
```javascript
// frontend/src/views/Chat.vue:394
await chatStore.joinMatchRoom(matchId.value)

// 應該發送 WebSocket 訊息
{
  type: 'join_match',
  match_id: matchId
}
```

**後端**:
```python
# backend/app/api/websocket.py:140-141
elif message_type == "join_match":
    await handle_join_match(message_data, user_id)
```

**驗證**: 檢查後端日誌是否有 "User XXX joined match room YYY"

---

### 問題 3：typing 事件沒有發送

**檢查點**:
```javascript
// frontend/src/views/Chat.vue:274-290
const handleTyping = () => {
  chatStore.sendTyping(matchId.value, true)

  // 3 秒後停止
  setTimeout(() => {
    chatStore.sendTyping(matchId.value, false)
  }, 3000)
}
```

**驗證**:
1. 打開瀏覽器控制台（F12）
2. 在聊天輸入框打字
3. 查看是否有日誌：`[Chat.vue] User typing, matchId: ...`
4. 查看 Network 是否有 WebSocket 訊息

---

### 問題 4：已讀回條邏輯錯誤

**檢查點**:
```javascript
// frontend/src/stores/chat.js:165-179
const markConversationAsRead = async (matchId) => {
  const unreadMessages = messages.value[matchId]
    .filter(m => !m.is_read && m.sender_id !== currentUserId())
    .map(m => m.id)

  if (unreadMessages.length > 0) {
    await markAsRead(unreadMessages)
  }
}
```

**可能原因**:
- `currentUserId()` 返回錯誤
- `messages.value[matchId]` 為空
- API `/messages/messages/read` 失敗

---

## 🔧 除錯步驟

### 步驟 1：檢查 WebSocket 連接狀態

**打開瀏覽器控制台（F12）** → Console 標籤

應該看到：
```
WebSocket connected, sending auth...
WebSocket authenticated successfully
```

---

### 步驟 2：檢查是否加入聊天室

**進入聊天室後**，控制台應該顯示：
```
[Chat.vue] Joining match room: xxx-xxx-xxx
```

**後端日誌**應該顯示：
```
User xxx joined match room yyy
```

如果沒有，說明 `joinMatchRoom` 沒有執行。

---

### 步驟 3：測試打字指示器

**在聊天輸入框打字**，控制台應該顯示：
```
[Chat.vue] User typing, matchId: xxx
[WebSocket] Sending typing indicator: { matchId, isTyping: true }
```

**對方瀏覽器**應該顯示：
```
[Chat] Received typing indicator: { match_id, user_id, is_typing: true }
[Chat] User typing: { ... }
```

如果看不到「Received typing indicator」，說明後端沒有廣播或前端沒有收到。

---

### 步驟 4：檢查已讀回條

**對方打開聊天**，控制台應該顯示：
```
標記訊息為已讀: [message_ids...]
```

**發送者瀏覽器**應該顯示：
```
[Chat] Received read receipt: { message_id, read_at }
```

---

## 💡 快速驗證方案

### 方案 1：添加臨時日誌

在 `frontend/src/stores/chat.js` 的 `handleTypingIndicator` 添加：

```javascript
const handleTypingIndicator = (data) => {
  console.log('🔥 [DEBUG] Typing indicator received:', data)  // ← 添加這行
  logger.debug('[Chat] Received typing indicator:', data)
  // ...
}
```

### 方案 2：檢查 match_rooms

**後端添加臨時日誌**（`backend/app/websocket/manager.py:161`）:

```python
async def send_to_match(self, match_id, message, exclude_user=None):
    print(f"🔥 [DEBUG] send_to_match called: match_id={match_id}")
    print(f"🔥 [DEBUG] match_rooms keys: {list(self.match_rooms.keys())}")
    print(f"🔥 [DEBUG] users in room: {self.match_rooms.get(match_id, [])}")
    # ...
```

---

## 🎯 最可能的原因

### 原因 1：沒有加入聊天室 ⭐⭐⭐⭐⭐

**檢查**:
```javascript
// frontend/src/views/Chat.vue:394
await chatStore.joinMatchRoom(matchId.value)
```

這行代碼會發送：
```json
{
  "type": "join_match",
  "match_id": "xxx"
}
```

後端收到後應該執行：
```python
await manager.join_match_room(str(match_id), user_id)
```

**如果沒有加入聊天室，typing 和其他廣播都收不到！**

---

### 原因 2：認證流程問題 ⭐⭐⭐⭐

新的認證流程（首次訊息認證）可能導致：
1. 認證完成前發送的 join_match 被忽略
2. onMessage 註冊時機錯誤

**檢查順序**:
```
1. connect() → 認證成功
2. initWebSocket() 註冊 handler
3. joinMatchRoom() 加入聊天室
```

如果順序錯誤（join_match 在認證前發送），就會失敗。

---

### 原因 3：currentMatchId 未設置 ⭐⭐⭐

```javascript
const isTyping = computed(() => {
  if (!currentMatchId.value) return false  // ← 這裡返回 false
  return !!typingUsers.value[currentMatchId.value]
})
```

**檢查**: `chatStore.currentMatchId` 是否有值

---

## 📝 建議除錯方案

### 立即檢查（5 分鐘）

打開兩個瀏覽器視窗，登入 Alice 和 Bob：

1. **打開控制台**（F12 → Console）
2. **清空日誌**（點擊 🚫 清除）
3. **進入聊天室**
4. **查看日誌**：
   - 是否有 "Joining match room"？
   - 是否有 "User typing"？
   - 是否有 "Received typing indicator"？

5. **在 Alice 視窗打字**
6. **在 Bob 視窗查看**：
   - Console 是否收到 typing 事件？
   - UI 是否顯示「正在輸入...」？

---

如果沒有收到 typing 事件，問題在後端廣播；
如果收到但沒顯示，問題在前端 UI 條件判斷。

---

需要我幫你添加除錯日誌嗎？或者你可以先按照上面的步驟檢查控制台日誌。