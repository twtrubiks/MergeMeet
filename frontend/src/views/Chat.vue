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
          </div>
        </div>

        <!-- 更多選項按鈕 -->
        <n-dropdown
          v-if="currentConversation"
          :options="moreOptions"
          @select="handleMoreAction"
          trigger="click"
        >
          <n-button text class="more-button">
            <template #icon>
              <n-icon size="24"><EllipsisVertical /></n-icon>
            </template>
          </n-button>
        </n-dropdown>
      </div>

      <!-- 訊息列表 -->
      <div ref="messageListRef" class="message-list" @scroll="handleScroll">
        <div v-if="!chatStore.currentMessages.length" class="empty-state">
          <n-empty description="還沒有訊息，開始聊天吧！" />
        </div>

        <div v-else class="messages-container">
          <!-- 載入更多指示器 -->
          <div v-if="isLoadingMore" class="loading-more">
            <n-spin size="small" />
            <span>載入中...</span>
          </div>
          <div v-else-if="!hasMore && chatStore.currentMessages.length > 0" class="no-more">
            <span>沒有更多訊息了</span>
          </div>

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

      <!-- 打字指示器（固定在輸入框上方） -->
      <div v-if="chatStore.isTyping" class="typing-indicator-fixed">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <span class="typing-text">{{ currentConversation?.other_user_name }} 正在輸入...</span>
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

    <!-- 舉報對話框 -->
    <ReportModal
      :show="showReportModal"
      :reported-user="reportedUserData"
      @close="showReportModal = false"
      @reported="handleReported"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NIcon, NAvatar, NInput, NEmpty, NSpin, NAlert, NDropdown, useMessage, useDialog } from 'naive-ui'
import { ArrowBack, Send, EllipsisVertical, BanOutline, AlertCircleOutline } from '@vicons/ionicons5'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { useSafetyStore } from '@/stores/safety'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import ReportModal from '@/components/ReportModal.vue'
import { logger } from '@/utils/logger'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const chatStore = useChatStore()
const userStore = useUserStore()
const safetyStore = useSafetyStore()

const matchId = computed(() => route.params.matchId)
const messageInput = ref('')
const messageListRef = ref(null)
const typingTimer = ref(null)
const defaultAvatar = 'https://via.placeholder.com/40'

// 分頁載入狀態
const currentPage = ref(1)
const hasMore = ref(true)
const isLoadingMore = ref(false)

// 舉報功能
const showReportModal = ref(false)
const reportedUserData = computed(() => {
  if (!currentConversation.value) return null
  return {
    user_id: currentConversation.value.other_user_id,
    display_name: currentConversation.value.other_user_name
  }
})

const currentConversation = computed(() => chatStore.currentConversation)
const otherUserId = computed(() => currentConversation.value?.other_user_id)

// 更多選項下拉選單
const moreOptions = computed(() => [
  {
    label: '封鎖用戶',
    key: 'block',
    icon: () => h(NIcon, null, { default: () => h(BanOutline) })
  },
  {
    label: '舉報用戶',
    key: 'report',
    icon: () => h(NIcon, null, { default: () => h(AlertCircleOutline) })
  }
])

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

// 處理更多選項動作
const handleMoreAction = (key) => {
  if (!otherUserId.value) {
    message.error('無法獲取用戶資訊')
    return
  }

  if (key === 'block') {
    handleBlockUser()
  } else if (key === 'report') {
    handleReportUser()
  }
}

// 封鎖用戶
const handleBlockUser = () => {
  dialog.warning({
    title: '封鎖用戶',
    content: `確定要封鎖 ${currentConversation.value?.other_user_name} 嗎？封鎖後將無法看到對方的個人資料、無法配對，且對方無法向你發送訊息。`,
    positiveText: '確定封鎖',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await safetyStore.blockUser(otherUserId.value, '從聊天頁面封鎖')
        message.success('已成功封鎖該用戶')
        // 封鎖成功後返回訊息列表
        router.push('/messages')
      } catch (error) {
        message.error(error.message || '封鎖失敗')
      }
    }
  })
}

// 舉報用戶
const handleReportUser = () => {
  if (!otherUserId.value) {
    message.error('無法獲取用戶資訊')
    return
  }
  showReportModal.value = true
}

// 舉報成功處理
const handleReported = () => {
  message.success('舉報已送出，感謝您的協助')
  showReportModal.value = false
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
  logger.debug('[Chat.vue] User typing, matchId:', matchId.value)

  // 發送正在打字的狀態
  chatStore.sendTyping(matchId.value, true)

  // 清除之前的計時器
  if (typingTimer.value) {
    clearTimeout(typingTimer.value)
  }

  // 3 秒後自動停止打字狀態
  typingTimer.value = setTimeout(() => {
    logger.debug('[Chat.vue] Typing timeout, sending stop')
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

// 載入更多歷史訊息
const loadMoreMessages = async () => {
  if (isLoadingMore.value || !hasMore.value) {
    return
  }

  isLoadingMore.value = true

  try {
    // 保存當前滾動高度
    const scrollHeightBefore = messageListRef.value?.scrollHeight || 0
    const scrollTopBefore = messageListRef.value?.scrollTop || 0

    // 載入下一頁
    const nextPage = currentPage.value + 1
    const result = await chatStore.fetchChatHistory(matchId.value, nextPage)

    // 檢查是否還有更多訊息
    if (result.messages && result.messages.length > 0) {
      currentPage.value = nextPage

      // 檢查是否還有下一頁
      const total = result.total || 0
      const loadedCount = currentPage.value * 50 // 假設每頁 50 條
      hasMore.value = loadedCount < total

      // 等待 DOM 更新後恢復滾動位置
      await nextTick()

      // 恢復滾動位置（加上新載入內容的高度）
      if (messageListRef.value) {
        const scrollHeightAfter = messageListRef.value.scrollHeight
        const heightDiff = scrollHeightAfter - scrollHeightBefore
        messageListRef.value.scrollTop = scrollTopBefore + heightDiff
      }
    } else {
      hasMore.value = false
    }
  } catch (error) {
    logger.error('載入更多訊息失敗:', error)
    message.error('載入更多訊息失敗')
  } finally {
    isLoadingMore.value = false
  }
}

// 處理滾動事件（實現滾動載入更多）
const handleScroll = () => {
  if (messageListRef.value) {
    const { scrollTop } = messageListRef.value

    // 如果滾動到頂部，載入更多歷史訊息
    if (scrollTop < 100 && !isLoadingMore.value && hasMore.value) {
      loadMoreMessages()
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
  // 重置分頁狀態
  currentPage.value = 1
  hasMore.value = true
  isLoadingMore.value = false

  // 初始化 WebSocket 並等待連接成功
  if (!chatStore.ws.isConnected) {
    try {
      await chatStore.initWebSocket()
      logger.debug('[Chat.vue] WebSocket connected successfully')
    } catch (error) {
      logger.error('[Chat.vue] Failed to connect WebSocket:', error)
      message.error('WebSocket 連接失敗')
    }
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

.more-button {
  font-size: 24px;
  flex-shrink: 0;
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

/* 打字指示器（固定在輸入框上方） */
.typing-indicator-fixed {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(24, 144, 255, 0.1);
  border-left: 3px solid #1890ff;
  font-size: 13px;
  color: #1890ff;
  animation: slideDown 0.3s ease;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #1890ff;
  animation: typing 1.4s infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

.typing-text {
  font-weight: 500;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-6px);
    opacity: 1;
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  color: #666;
  font-size: 14px;
}

.no-more {
  display: flex;
  justify-content: center;
  padding: 12px;
  color: #999;
  font-size: 12px;
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
