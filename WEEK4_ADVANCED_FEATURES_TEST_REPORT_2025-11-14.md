# Week 4 進階功能測試報告

**測試日期**: 2025-11-14
**測試人員**: Claude Code
**測試範圍**: Week 4 進階聊天功能（已讀狀態、刪除訊息、打字指示器）
**狀態**: ⚠️ 發現多個問題

---

## 📋 測試摘要

### 測試環境
- ✅ 前端：http://localhost:5173
- ✅ 後端：http://localhost:8000
- ✅ WebSocket：連接正常
- ✅ 測試帳號：Alice & Bob（已配對）

### 整體結果
- ❌ **0/3 功能完全可用**
- ⚠️ **3/3 功能發現問題**

---

## 🔍 功能測試詳情

### 4.5 已讀狀態

#### 測試項目

| 測試項目 | 預期結果 | 實際結果 | 狀態 |
|---------|---------|---------|------|
| 進入聊天室自動標記為已讀 | API 調用 POST /messages/read | ❌ 未調用 API | ❌ 失敗 |
| 訊息顯示已讀狀態 | ✓✓ 已讀 | ✓ 已送達（未改變） | ❌ 失敗 |
| 已讀回執通知發送者 | 發送者看到 ✓✓ 已讀 | 發送者看到 ✓ 已送達 | ❌ 失敗 |

#### 🐛 發現的 Bug

**Bug #1: 已讀狀態競態條件**

**位置**: `frontend/src/stores/chat.js:210-221`

**問題代碼**:
```javascript
const joinMatchRoom = (matchId) => {
  currentMatchId.value = matchId
  ws.joinMatch(matchId)

  // 獲取聊天記錄
  if (!messages.value[matchId]) {
    fetchChatHistory(matchId)  // ❌ async 但未 await
  }

  // 標記已讀
  markConversationAsRead(matchId)  // ❌ 在訊息載入前就執行
}
```

**問題分析**:
1. `fetchChatHistory()` 是 async 函數，但沒有使用 `await`
2. `markConversationAsRead()` 立即執行，此時 `messages.value[matchId]` 仍為 `undefined`
3. `markConversationAsRead()` 內部檢查失敗並提前返回：
   ```javascript
   if (!messages.value[matchId]) return  // ← 提前返回
   ```

**驗證結果**:
- ✅ 後端 API 存在：`POST /api/messages/messages/read`
- ✅ 前端函數存在：`markAsRead()`, `markConversationAsRead()`
- ❌ Network 標籤沒有 `/messages/read` 請求
- ❌ 所有訊息的 `is_read` 字段為 `null`

**建議修復**:
```javascript
const joinMatchRoom = async (matchId) => {
  currentMatchId.value = matchId
  ws.joinMatch(matchId)

  // 獲取聊天記錄
  if (!messages.value[matchId]) {
    await fetchChatHistory(matchId)  // ✅ 加上 await
  }

  // 標記已讀（確保訊息已載入）
  markConversationAsRead(matchId)
}
```

**影響範圍**: 中等
- 用戶無法看到訊息已讀狀態
- 發送者不知道訊息是否被閱讀

---

### 4.6 刪除訊息

#### 測試項目

| 測試項目 | 預期結果 | 實際結果 | 狀態 |
|---------|---------|---------|------|
| 長按訊息顯示刪除選項 | 顯示刪除按鈕或選單 | ❌ 無任何 UI | ❌ 失敗 |
| 點擊刪除訊息 | 訊息被刪除 | ❌ 無法測試（無 UI） | ❌ 失敗 |
| 刪除後顯示效果 | 訊息消失或顯示「已刪除」 | ❌ 無法測試 | ❌ 失敗 |

#### ⚠️ 發現的問題

**問題 #1: 缺少刪除 UI**

**位置**: `frontend/src/components/chat/MessageBubble.vue`

**問題分析**:
- ✅ 後端 API 存在：`DELETE /api/messages/messages/{message_id}` (messages.py:257)
- ✅ 前端函數存在：`deleteMessage(messageId)` in chat.js:178-197
- ❌ **MessageBubble.vue 完全沒有刪除 UI**
  - 無刪除按鈕
  - 無右鍵選單（Context Menu）
  - 無長按事件處理器
  - 無任何方式觸發刪除功能

**MessageBubble.vue 結構**:
```vue
<template>
  <div class="message-bubble">
    <!-- 頭像 -->
    <div class="message-avatar">...</div>

    <!-- 訊息內容 -->
    <div class="message-content">{{ message.content }}</div>

    <!-- 時間與狀態 -->
    <div class="message-info">
      <span class="message-time">{{ formattedTime }}</span>
      <span class="message-status">✓ 已送達</span>
    </div>

    <!-- ❌ 沒有刪除按鈕或操作 -->
  </div>
</template>
```

**建議實現**:

**方案 A: 長按刪除**（推薦）
```vue
<template>
  <div
    class="message-bubble"
    @contextmenu.prevent="showDeleteMenu"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >
    <!-- 訊息內容 -->

    <!-- 刪除選單 -->
    <n-dropdown
      v-model:show="showMenu"
      :options="menuOptions"
      @select="handleMenuSelect"
    >
      <div></div>
    </n-dropdown>
  </div>
</template>

<script setup>
const emit = defineEmits(['delete'])
const showMenu = ref(false)
const menuOptions = [
  { label: '刪除訊息', key: 'delete', icon: TrashIcon }
]

const showDeleteMenu = (e) => {
  if (props.isOwn) {
    showMenu.value = true
  }
}

const handleMenuSelect = (key) => {
  if (key === 'delete') {
    emit('delete', props.message.id)
  }
}
</script>
```

**方案 B: 滑動刪除**（移動端友好）
```vue
<template>
  <n-swipe
    ref="swipeRef"
    :threshold="60"
    @swipe-left="onSwipeLeft"
  >
    <template #default>
      <!-- 訊息內容 -->
    </template>
    <template #right>
      <n-button type="error" @click="handleDelete">
        刪除
      </n-button>
    </template>
  </n-swipe>
</template>
```

**影響範圍**: 高
- 功能完全無法使用
- 用戶無法刪除誤發的訊息

---

### 4.7 打字指示器

#### 測試項目

| 測試項目 | 預期結果 | 實際結果 | 狀態 |
|---------|---------|---------|------|
| Alice 打字時 Bob 看到提示 | 顯示「正在輸入...」 | ❌ 無顯示 | ❌ 失敗 |
| 停止打字 3 秒後提示消失 | 提示消失 | ❌ 無法測試 | ❌ 失敗 |
| 對方離開聊天室時提示消失 | 提示消失 | ❌ 無法測試 | ❌ 失敗 |

#### ⚠️ 發現的問題

**問題 #1: 打字指示器未觸發**

**測試步驟**:
1. Alice 登入，進入與 Bob 的聊天室
2. Bob 登入，進入與 Alice 的聊天室
3. 在 Alice 的輸入框輸入文字（通過 JavaScript 觸發 input 事件）
4. 檢查 Bob 的頁面

**預期結果**:
- Bob 的聊天室頭部應顯示「正在輸入...」

**實際結果**:
- ❌ Bob 頁面無任何變化
- ❌ 未顯示「正在輸入...」

**代碼審查**:

**Chat.vue 已實現 UI** (frontend/src/views/Chat.vue:21-23):
```vue
<div v-if="chatStore.isTyping" class="typing-indicator">
  正在輸入...
</div>
```

**Chat.vue 已實現輸入處理** (frontend/src/views/Chat.vue:139-153):
```javascript
const handleTyping = () => {
  // 發送正在打字的狀態
  chatStore.sendTyping(matchId.value, true)

  // 清除之前的計時器
  if (typingTimer.value) {
    clearTimeout(typingTimer.value)
  }

  // 3 秒後自動停止打字狀態
  typingTimer.value = setTimeout(() => {
    chatStore.sendTyping(matchId.value, false)
  }, 3000)
}
```

**WebSocket 發送實現** (useWebSocket.js:162-168):
```javascript
const sendTypingIndicator = (matchId, isTyping) => {
  return send({
    type: 'typing',
    match_id: matchId,
    is_typing: isTyping
  })
}
```

**WebSocket 接收處理** (chat.js:272-286):
```javascript
const handleTypingIndicator = (data) => {
  const { match_id, user_id, is_typing } = data

  if (is_typing) {
    typingUsers.value[match_id] = user_id
    // 3 秒後自動清除
    setTimeout(() => {
      if (typingUsers.value[match_id] === user_id) {
        delete typingUsers.value[match_id]
      }
    }, 3000)
  } else {
    delete typingUsers.value[match_id]
  }
}
```

**可能原因分析**:
1. **WebSocket 事件未正確發送** - WebSocket 可能未成功發送 typing 事件
2. **後端未正確轉發** - 後端 WebSocket 處理器可能未處理 typing 事件
3. **事件監聽器未註冊** - `ws.onMessage('typing', ...)` 可能未正確註冊
4. **matchId 不一致** - 發送和接收的 match_id 可能不一致

**需要進一步調查**:
- 檢查 WebSocket 實際發送的訊息（通過 Chrome DevTools → Network → WS）
- 檢查後端 WebSocket 處理器代碼
- 添加 console.log 追蹤事件流程

**影響範圍**: 低
- 不影響核心聊天功能
- 僅影響用戶體驗

---

## 📊 測試統計

### 功能完成度

| 功能 | 後端 API | 前端邏輯 | UI 實現 | 實際可用 | 狀態 |
|------|---------|---------|---------|---------|------|
| 已讀狀態 | ✅ 完成 | ✅ 完成 | ✅ 完成 | ❌ Bug | ⚠️ 需修復 |
| 刪除訊息 | ✅ 完成 | ✅ 完成 | ❌ 缺失 | ❌ 不可用 | ⚠️ 需實現 |
| 打字指示器 | ❓ 未知 | ✅ 完成 | ✅ 完成 | ❌ 不可用 | ⚠️ 需調查 |

### Bug 優先級

| Bug ID | 功能 | 嚴重程度 | 優先級 | 預計修復時間 |
|--------|------|---------|-------|------------|
| #1 | 已讀狀態競態條件 | 中 | 高 | 10 分鐘 |
| #2 | 刪除訊息無 UI | 高 | 中 | 2 小時 |
| #3 | 打字指示器失效 | 低 | 低 | 1 小時 |

---

## 🔧 建議修復計劃

### 立即修復（高優先級）

#### 1. 修復已讀狀態 Bug (10 分鐘)

**檔案**: `frontend/src/stores/chat.js`

**修改**:
```javascript
// 修改前
const joinMatchRoom = (matchId) => {
  currentMatchId.value = matchId
  ws.joinMatch(matchId)

  if (!messages.value[matchId]) {
    fetchChatHistory(matchId)
  }

  markConversationAsRead(matchId)
}

// 修改後
const joinMatchRoom = async (matchId) => {
  currentMatchId.value = matchId
  ws.joinMatch(matchId)

  if (!messages.value[matchId]) {
    await fetchChatHistory(matchId)
  }

  // 確保訊息已載入後再標記已讀
  await markConversationAsRead(matchId)
}
```

同時修改 `markConversationAsRead` 為 async:
```javascript
const markConversationAsRead = async (matchId) => {
  if (!messages.value[matchId]) return

  const unreadMessages = messages.value[matchId]
    .filter(m => !m.is_read && m.sender_id !== currentUserId())
    .map(m => m.id)

  if (unreadMessages.length > 0) {
    await markAsRead(unreadMessages)

    const conv = conversations.value.find(c => c.match_id === matchId)
    if (conv) {
      conv.unread_count = 0
    }
  }
}
```

### 中期實現（中優先級）

#### 2. 實現刪除訊息 UI (2 小時)

**步驟**:
1. 修改 `MessageBubble.vue` 添加右鍵選單或長按事件
2. 添加刪除確認對話框
3. 連接 `chatStore.deleteMessage()` 函數
4. 更新 UI 顯示刪除後的狀態

**參考實現**: 見上方「方案 A: 長按刪除」

### 後續調查（低優先級）

#### 3. 調查打字指示器問題 (1 小時)

**調查步驟**:
1. 在 Chrome DevTools → Network → WS 標籤查看 WebSocket 訊息
2. 檢查後端 WebSocket 處理器是否處理 `typing` 事件
3. 添加 console.log 追蹤整個事件流程:
   ```javascript
   const handleTyping = () => {
     console.log('[Typing] Sending typing event:', matchId.value)
     chatStore.sendTyping(matchId.value, true)
     // ...
   }

   const handleTypingIndicator = (data) => {
     console.log('[Typing] Received typing event:', data)
     // ...
   }
   ```
4. 確認 WebSocket 事件監聽器正確註冊

---

## ✅ 測試結論

### 核心問題
1. **已讀狀態功能有競態條件 Bug**，導致功能無法使用
2. **刪除訊息功能缺少 UI**，用戶無法觸發
3. **打字指示器功能未生效**，需要進一步調查

### 生產就緒評估
- ❌ **不建議上線** - 已讀狀態 Bug 影響用戶體驗
- ⚠️ **需要修復** - 刪除訊息功能不完整
- ℹ️ **可選功能** - 打字指示器為輔助功能，不影響核心使用

### 建議行動
1. ✅ **立即修復已讀狀態 Bug** - 預計 10 分鐘
2. ⚠️ **實現刪除訊息 UI** - 預計 2 小時（可延後）
3. ℹ️ **調查打字指示器** - 預計 1 小時（可延後）

**總預計修復時間**: 3 小時 10 分鐘（核心功能 10 分鐘）

---

## 📝 附錄

### 測試數據

**API 響應範例** (GET /messages/matches/{match_id}/messages):
```json
{
  "messages": [
    {
      "id": "04696380-f2e1-4408-81ff-6890862181d2",
      "match_id": "096f4f86-7ba1-4c1f-9b31-e99e163b8c8f",
      "sender_id": "40da5a77-2a29-410c-9ee3-1109e18593e5",
      "content": "修復測試：登入後立即可以聊天，無需重新載入！",
      "message_type": "TEXT",
      "is_read": null,  // ← 應該為 true/false，但為 null
      "sent_at": "2025-11-14T09:45:24.104657Z"
    }
  ]
}
```

### 相關文件
- `frontend/src/stores/chat.js` - 聊天狀態管理（含 Bug）
- `frontend/src/components/chat/MessageBubble.vue` - 訊息氣泡組件（缺 UI）
- `frontend/src/views/Chat.vue` - 聊天頁面（打字處理）
- `frontend/src/composables/useWebSocket.js` - WebSocket 處理
- `backend/app/api/messages.py:257` - 刪除訊息 API

---

**測試完成時間**: 2025-11-14
**下次測試計劃**: 修復 Bug 後重新驗證功能

