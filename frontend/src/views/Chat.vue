<template>
  <div class="chat-page">
    <n-spin :show="chatStore.loading">
      <!-- 聊天室頭部 -->
      <div class="chat-header">
        <n-button text @click="goBack" class="back-button">
          <template #icon>
            <n-icon><ArrowBack /></n-icon>
          </template>
        </n-button>

        <div v-if="currentConversation" class="chat-user-info">
          <n-avatar
            :src="currentConversation.other_user_avatar"
            :fallback-src="defaultAvatar"
            size="medium"
            round
          />
          <div class="user-details">
            <div class="user-name">{{ currentConversation.other_user_name }}</div>
            <div v-if="chatStore.isTyping" class="typing-indicator">
              正在輸入...
            </div>
          </div>
        </div>
      </div>

      <!-- 訊息列表 -->
      <div ref="messageListRef" class="message-list" @scroll="handleScroll">
        <div v-if="!chatStore.currentMessages.length" class="empty-state">
          <n-empty description="還沒有訊息，開始聊天吧！" />
        </div>

        <div v-else class="messages-container">
          <MessageBubble
            v-for="message in chatStore.currentMessages"
            :key="message.id"
            :message="message"
            :is-own="message.sender_id === userStore.user?.id"
            :show-avatar="message.sender_id !== userStore.user?.id"
            :other-user-avatar="currentConversation?.other_user_avatar"
            @delete="handleDeleteMessage"
          />
        </div>
      </div>

      <!-- 輸入區域 -->
      <div class="chat-input-area">
        <n-input
          v-model:value="messageInput"
          type="textarea"
          placeholder="輸入訊息..."
          :autosize="{
            minRows: 1,
            maxRows: 4
          }"
          @keydown.enter.exact="handleSendMessage"
          @input="handleTyping"
          :disabled="!chatStore.ws.isConnected"
        />
        <n-button
          type="primary"
          :disabled="!messageInput.trim() || !chatStore.ws.isConnected"
          @click="handleSendMessage"
          class="send-button"
        >
          <template #icon>
            <n-icon><Send /></n-icon>
          </template>
          發送
        </n-button>
      </div>

      <!-- WebSocket 連接狀態提示 -->
      <div v-if="!chatStore.ws.isConnected" class="connection-warning">
        <n-alert type="warning" :show-icon="false">
          連接已斷開，正在重新連接...
        </n-alert>
      </div>
    </n-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NIcon, NAvatar, NInput, NEmpty, NSpin, NAlert, useMessage, useDialog } from 'naive-ui'
import { ArrowBack, Send } from '@vicons/ionicons5'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import MessageBubble from '@/components/chat/MessageBubble.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const chatStore = useChatStore()
const userStore = useUserStore()

const matchId = computed(() => route.params.matchId)
const messageInput = ref('')
const messageListRef = ref(null)
const typingTimer = ref(null)
const defaultAvatar = 'https://via.placeholder.com/40'

const currentConversation = computed(() => chatStore.currentConversation)

// 返回上一頁
const goBack = () => {
  router.push('/messages')
}

// 刪除訊息
const handleDeleteMessage = (messageId) => {
  dialog.warning({
    title: '刪除訊息',
    content: '確定要刪除這則訊息嗎？此操作無法復原。',
    positiveText: '刪除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await chatStore.deleteMessage(messageId)
        message.success('訊息已刪除')
      } catch (error) {
        message.error(error.message || '刪除失敗')
      }
    }
  })
}

// 發送訊息
const handleSendMessage = async (event) => {
  // 如果是 Shift + Enter，允許換行
  if (event?.shiftKey) {
    return
  }

  event?.preventDefault()

  if (!messageInput.value.trim()) {
    return
  }

  try {
    await chatStore.sendMessage(matchId.value, messageInput.value.trim())
    messageInput.value = ''

    // 停止打字指示器
    chatStore.sendTyping(matchId.value, false)

    // 滾動到底部
    await nextTick()
    scrollToBottom()
  } catch (error) {
    message.error(error.message || '發送失敗')
  }
}

// 處理打字事件
const handleTyping = () => {
  console.log('[Chat.vue] User typing, matchId:', matchId.value)

  // 發送正在打字的狀態
  chatStore.sendTyping(matchId.value, true)

  // 清除之前的計時器
  if (typingTimer.value) {
    clearTimeout(typingTimer.value)
  }

  // 3 秒後自動停止打字狀態
  typingTimer.value = setTimeout(() => {
    console.log('[Chat.vue] Typing timeout, sending stop')
    chatStore.sendTyping(matchId.value, false)
  }, 3000)
}

// 滾動到底部
const scrollToBottom = (smooth = true) => {
  if (messageListRef.value) {
    messageListRef.value.scrollTo({
      top: messageListRef.value.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto'
    })
  }
}

// 處理滾動事件（實現滾動載入更多）
const handleScroll = () => {
  if (messageListRef.value) {
    const { scrollTop } = messageListRef.value

    // 如果滾動到頂部，載入更多歷史訊息
    if (scrollTop < 100) {
      // TODO: 實作載入更多歷史訊息
      console.log('Load more messages...')
    }
  }
}

// 監聽訊息變化，自動滾動到底部
watch(
  () => chatStore.currentMessages.length,
  async (newLength, oldLength) => {
    if (newLength > oldLength) {
      await nextTick()
      scrollToBottom()
    }
  }
)

onMounted(async () => {
  // 初始化 WebSocket
  if (!chatStore.ws.isConnected) {
    chatStore.initWebSocket()
  }

  // 載入對話列表（如果還沒載入）
  if (chatStore.conversations.length === 0) {
    await chatStore.fetchConversations()
  }

  // 加入聊天室（等待訊息載入和已讀標記完成）
  await chatStore.joinMatchRoom(matchId.value)

  // 滾動到底部
  await nextTick()
  scrollToBottom(false)
})

onUnmounted(() => {
  // 離開聊天室
  chatStore.leaveMatchRoom()

  // 清除打字計時器
  if (typingTimer.value) {
    clearTimeout(typingTimer.value)
  }
})
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
}

.chat-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background-color: white;
  border-bottom: 1px solid #e5e5e5;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  gap: 12px;
}

.back-button {
  font-size: 24px;
}

.chat-user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.typing-indicator {
  font-size: 12px;
  color: #1890ff;
  font-style: italic;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background-color: #f5f5f5;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.messages-container {
  display: flex;
  flex-direction: column;
}

.chat-input-area {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background-color: white;
  border-top: 1px solid #e5e5e5;
  align-items: flex-end;
}

.chat-input-area :deep(.n-input) {
  flex: 1;
}

.send-button {
  flex-shrink: 0;
}

.connection-warning {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  width: 90%;
  max-width: 400px;
}

/* 滾動條樣式 */
.message-list::-webkit-scrollbar {
  width: 6px;
}

.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.message-list::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.message-list::-webkit-scrollbar-thumb:hover {
  background: #999;
}
</style>
