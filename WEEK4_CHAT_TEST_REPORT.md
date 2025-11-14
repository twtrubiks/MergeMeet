# Week 4 進階聊天功能測試報告

**測試日期**: 2025-11-14
**測試範圍**: 已讀狀態、刪除訊息、打字指示器
**測試環境**: Chrome DevTools Protocol 自動化測試

---

## 修復的問題

### 1. ✅ Critical Bug: CommonJS require() 錯誤
**檔案**: `frontend/src/stores/chat.js:372-376`

**問題描述**:
```javascript
// ❌ 錯誤：瀏覽器不支援 require()
function useAuthStore() {
  const { useUserStore } = require('./user')
  return useUserStore()
}
```

**修復方案**:
```javascript
// ✅ 正確：使用 ES6 import
import { useUserStore } from './user'

const currentUserId = () => {
  const userStore = useUserStore()
  return userStore.user?.id
}
```

**影響**: 此錯誤導致整個聊天功能無法運作
**Commit**: `8cfc5b8`

---

### 2. ✅ 打字指示器響應式更新問題
**檔案**: `frontend/src/stores/chat.js:273-295`

**問題描述**:
直接修改 ref 物件的屬性不會觸發 Vue 響應式更新：
```javascript
// ❌ 不觸發響應式
typingUsers.value[match_id] = user_id
delete typingUsers.value[match_id]
```

**修復方案**:
```javascript
// ✅ 使用 spread operator 創建新物件
typingUsers.value = { ...typingUsers.value, [match_id]: user_id }

// ✅ 使用解構移除屬性
const { [match_id]: _, ...rest } = typingUsers.value
typingUsers.value = rest
```

**Commit**: `e327208`

---

## 測試結果

### 1. ✅ 已讀狀態功能 - 測試通過

**測試項目**:
- API 調用: `POST /api/messages/messages/read` → **200 OK**
- 狀態顯示: 訊息顯示 "✓✓ 已讀" → **正常**
- 自動標記已讀: 進入對話自動標記未讀訊息 → **正常**

**結論**: 功能完全正常 ✅

---

### 2. ⚠️ 刪除訊息功能 - 部分測試通過

**測試項目**:
- 右鍵選單顯示 → **正常** ✅
- "刪除訊息" 選項 → **正常** ✅
- 程式碼實現 (`useDialog`, `handleDeleteMessage`) → **正確** ✅
- 確認對話框觸發 → **自動化測試無法驗證** ⚠️

**原因**: Vue 的 dialog 需要真實用戶互動才能觸發（自動化測試限制）

**結論**: 程式碼實現正確，需要手動測試驗證完整流程 ⚠️

---

### 3. ⚠️ 打字指示器功能 - 發現問題

#### 正常工作的部分 ✅
1. **WebSocket 連接**: 正常
2. **訊息發送**: 正常（聊天訊息收發正常）
3. **打字事件發送**:
   - Console 日誌顯示正確發送
   - 數據格式正確: `{type: 'typing', match_id: '...', is_typing: true}`
4. **前端響應式狀態**: 已修復

#### 發現的問題 ❌
**現象**: 接收端沒有收到 typing 事件
- Alice 打字時，Bob 的 Console **沒有任何日誌**
- Bob 打字時，Alice 的 Console **沒有任何日誌**
- 但聊天訊息可以正常互相收發

#### 可能原因分析

**原因 1: Match Room 加入失敗**
```javascript
// frontend/src/stores/chat.js:211-222
const joinMatchRoom = async (matchId) => {
  currentMatchId.value = matchId
  ws.joinMatch(matchId)  // 發送 join_match 事件

  if (!messages.value[matchId]) {
    await fetchChatHistory(matchId)
  }

  await markConversationAsRead(matchId)
}
```

**檢查項目**:
- [ ] 後端是否收到 `join_match` 事件？
- [ ] `manager.match_rooms` 是否包含兩個用戶？
- [ ] 前端是否收到 `joined_match` 確認訊息？

**原因 2: 後端廣播問題**
```python
# backend/app/api/websocket.py:196-219
async def handle_typing_indicator(data: dict, user_id: str):
    match_id = data.get("match_id")
    is_typing = data.get("is_typing", False)

    await manager.send_to_match(
        match_id,
        {
            "type": "typing",
            "user_id": user_id,
            "is_typing": is_typing,
            "match_id": match_id
        },
        exclude_user=user_id  # 排除發送者
    )
```

**檢查項目**:
- [ ] 後端是否收到 typing 事件？（查看 uvicorn 日誌）
- [ ] `send_to_match` 是否成功執行？
- [ ] `match_rooms[match_id]` 是否包含接收者？

**原因 3: 前端訊息處理器未正確註冊**
```javascript
// frontend/src/stores/chat.js:45-53
const initWebSocket = () => {
  ws.connect()

  // 註冊訊息處理器
  ws.onMessage('new_message', handleNewMessage)
  ws.onMessage('typing', handleTypingIndicator)  // 是否成功註冊？
  ws.onMessage('read_receipt', handleReadReceipt)
}
```

**檢查項目**:
- [ ] 頁面重新載入後，`initWebSocket()` 是否被調用？
- [ ] `handleTypingIndicator` 是否正確綁定？

---

## 建議的調試步驟

### Step 1: 檢查後端日誌
```bash
# 查看 uvicorn 日誌，確認是否收到事件
# 應該看到類似的日誌：
# - "User {user_id} joined match room {match_id}"
# - WebSocket typing 事件處理日誌
```

### Step 2: 添加後端調試日誌
在 `handle_typing_indicator` 和 `send_to_match` 添加日誌：
```python
async def handle_typing_indicator(data: dict, user_id: str):
    match_id = data.get("match_id")
    is_typing = data.get("is_typing", False)

    logger.info(f"[Typing] User {user_id} typing in match {match_id}: {is_typing}")
    logger.info(f"[Typing] Match rooms: {manager.match_rooms.get(match_id, [])}")

    await manager.send_to_match(
        match_id,
        {
            "type": "typing",
            "user_id": user_id,
            "is_typing": is_typing,
            "match_id": match_id
        },
        exclude_user=user_id
    )

    logger.info(f"[Typing] Broadcast completed")
```

### Step 3: 檢查 WebSocket 訊息
使用瀏覽器開發者工具：
1. 打開 Network 面板
2. 切換到 WS (WebSocket) 標籤
3. 查看實際收發的 WebSocket 訊息

### Step 4: 手動測試
在真實瀏覽器中：
1. 打開兩個不同的瀏覽器（或無痕模式）
2. 分別登入 Alice 和 Bob
3. 進入同一個聊天室
4. 測試打字指示器是否出現

---

## 需要手動測試的項目

1. **刪除訊息完整流程**
   - 右鍵點擊自己的訊息
   - 點擊 "刪除訊息"
   - 確認對話框是否出現
   - 點擊 "刪除" 按鈕
   - 驗證訊息是否從列表中移除

2. **打字指示器完整流程**
   - 兩個用戶同時進入聊天室
   - 一方開始輸入
   - 另一方是否看到 "正在輸入..."
   - 停止輸入 3 秒後指示器是否消失

---

## 總結

| 功能 | 狀態 | 說明 |
|------|------|------|
| 已讀狀態 | ✅ 通過 | 完全正常 |
| 刪除訊息 | ⚠️ 需手動測試 | 程式碼正確，自動化測試限制 |
| 打字指示器 | ❌ 需修復 | 發送正常，接收失敗 |

**建議優先級**:
1. **高優先級**: 修復打字指示器接收問題（影響用戶體驗）
2. **中優先級**: 手動驗證刪除訊息功能
3. **低優先級**: 優化自動化測試覆蓋率

---

**測試人員**: Claude Code
**報告生成**: 2025-11-14
