<template>
  <div class="chat-list-page">
    <!-- 返回主選單按鈕 -->
    <router-link to="/" class="back-home-btn">
      <n-icon size="20"><Home /></n-icon>
      <span>返回主選單</span>
    </router-link>

    <div class="page-header">
      <h1 class="page-title">訊息</h1>
      <n-badge :value="chatStore.unreadCount" :max="99" :show="chatStore.unreadCount > 0">
        <n-button text @click="handleNotificationClick">
          <template #icon>
            <n-icon size="24"><Notifications /></n-icon>
          </template>
        </n-button>
      </n-badge>
    </div>

    <n-spin :show="chatStore.loading">
      <div class="chat-list-container">
        <!-- 空狀態 -->
        <div v-if="!chatStore.loading && chatStore.conversations.length === 0" class="empty-state">
          <n-empty description="還沒有對話">
            <template #extra>
              <n-button type="primary" @click="goToDiscovery">
                開始探索
              </n-button>
            </template>
          </n-empty>
        </div>

        <!-- 對話列表 -->
        <div v-else class="conversation-list">
          <div
            v-for="conversation in chatStore.conversations"
            :key="conversation.match_id"
            class="conversation-item"
            @click="openChat(conversation.match_id)"
          >
            <!-- 用戶頭像 -->
            <n-badge
              :value="conversation.unread_count"
              :max="99"
              :show="conversation.unread_count > 0"
              class="avatar-badge"
            >
              <n-avatar
                :src="conversation.other_user_avatar"
                :fallback-src="defaultAvatar"
                size="large"
                round
              />
            </n-badge>

            <!-- 對話資訊 -->
            <div class="conversation-info">
              <div class="conversation-header">
                <span class="user-name">{{ conversation.other_user_name }}</span>
                <span v-if="conversation.last_message" class="message-time">
                  {{ formatTime(conversation.last_message.sent_at) }}
                </span>
              </div>

              <div class="conversation-preview">
                <span
                  v-if="conversation.last_message"
                  :class="['last-message', { 'unread': conversation.unread_count > 0 }]"
                >
                  {{ getMessagePreview(conversation.last_message) }}
                </span>
                <span v-else class="no-message">
                  開始聊天吧！
                </span>
              </div>
            </div>

            <!-- 箭頭圖示 -->
            <n-icon size="20" class="arrow-icon">
              <ChevronForward />
            </n-icon>
          </div>
        </div>
      </div>
    </n-spin>

    <!-- WebSocket 連接狀態 -->
    <div v-if="!chatStore.ws.isConnected" class="connection-warning">
      <n-alert type="warning" :show-icon="false" size="small">
        連接已斷開
      </n-alert>
    </div>
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NBadge, NButton, NIcon, NAvatar, NEmpty, NSpin, NAlert, useMessage } from 'naive-ui'
import { Notifications, ChevronForward, Home } from '@vicons/ionicons5'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const message = useMessage()
const chatStore = useChatStore()
const userStore = useUserStore()

const defaultAvatar = 'https://via.placeholder.com/50'

// 前往探索頁面
const goToDiscovery = () => {
  router.push('/discovery')
}

// 處理通知點擊
const handleNotificationClick = () => {
  // 可以在這裡實現通知面板或標記所有訊息為已讀等功能
  message.info('目前沒有新通知')
}

// 開啟聊天視窗
const openChat = (matchId) => {
  router.push(`/messages/${matchId}`)
}

// 格式化時間
const formatTime = (timestamp) => {
  if (!timestamp) return ''

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '剛剛'
  if (diffMins < 60) return `${diffMins} 分鐘前`
  if (diffHours < 24) return `${diffHours} 小時前`
  if (diffDays < 7) return `${diffDays} 天前`

  return date.toLocaleDateString('zh-TW', {
    month: 'short',
    day: 'numeric'
  })
}

// 獲取訊息預覽
const getMessagePreview = (message) => {
  if (!message) return ''

  const isOwn = message.sender_id === userStore.user?.id
  const prefix = isOwn ? '你: ' : ''

  // 限制長度
  const maxLength = 50
  const content = message.content || ''

  if (content.length > maxLength) {
    return prefix + content.substring(0, maxLength) + '...'
  }

  return prefix + content
}

onMounted(async () => {
  try {
    // 初始化 WebSocket
    if (!chatStore.ws.isConnected) {
      chatStore.initWebSocket()
    }

    // 載入對話列表
    await chatStore.fetchConversations()
  } catch (error) {
    message.error('載入對話列表失敗')
    console.error(error)
  }
})
</script>

<style scoped>
.chat-list-page {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* 返回主選單按鈕 */
.back-home-btn {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 100;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.95);
  color: #18a058;
  text-decoration: none;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.9rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.back-home-btn:hover {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(24, 160, 88, 0.2);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background-color: white;
  border-bottom: 1px solid #e5e5e5;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
  color: #333;
}

.chat-list-container {
  min-height: calc(100vh - 72px);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.conversation-list {
  background-color: white;
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  gap: 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s;
}

.conversation-item:hover {
  background-color: #f8f8f8;
}

.conversation-item:active {
  background-color: #f0f0f0;
}

.avatar-badge {
  flex-shrink: 0;
}

.conversation-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conversation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-time {
  font-size: 12px;
  color: #999;
  white-space: nowrap;
  flex-shrink: 0;
}

.conversation-preview {
  display: flex;
  align-items: center;
}

.last-message {
  font-size: 14px;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.last-message.unread {
  color: #333;
  font-weight: 600;
}

.no-message {
  font-size: 14px;
  color: #999;
  font-style: italic;
}

.arrow-icon {
  flex-shrink: 0;
  color: #ccc;
}

.connection-warning {
  position: fixed;
  top: 72px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  width: 90%;
  max-width: 400px;
}
</style>
