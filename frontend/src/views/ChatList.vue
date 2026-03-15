<template>
  <div class="chat-list-page">
    <div class="page-header">
      <!-- 返回主選單按鈕 -->
      <router-link to="/" class="back-home-btn">
        <Icon name="home" size="sm" decorative />
        <span>返回主選單</span>
      </router-link>

      <h1 class="page-title">訊息</h1>

      <!-- 通知鈴鐺已移至全域 NavBar -->
      <div class="header-spacer"></div>
    </div>

    <!-- 載入中 - 使用 Skeleton Loader -->
    <div v-if="chatStore.loading" class="loading-skeleton">
      <div class="conversation-list skeleton-list">
        <SkeletonListItem v-for="i in 5" :key="i" variant="chat" />
      </div>
    </div>

    <div v-else class="chat-list-container">
      <!-- 空狀態 -->
      <div v-if="chatStore.conversations.length === 0" class="empty-state">
        <div class="empty-animation">
          <span class="empty-chat">💬</span>
        </div>
        <h2>還沒有對話</h2>
        <p>開始探索並配對來開啟對話！</p>
        <AnimatedButton variant="primary" @click="goToDiscovery">
          <Icon name="search" size="sm" decorative /> 開始探索
        </AnimatedButton>
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
                :class="['last-message', { unread: conversation.unread_count > 0 }]"
              >
                {{ getMessagePreview(conversation.last_message) }}
              </span>
              <span v-else class="no-message"> 開始聊天吧！ </span>
            </div>
          </div>

          <!-- 箭頭圖示 -->
          <Icon name="chevron-forward" size="sm" decorative class="arrow-icon" />
        </div>
      </div>
    </div>

    <!-- WebSocket 連接狀態 -->
    <div v-if="!wsStore.isConnected" class="connection-warning">
      <n-alert type="warning" :show-icon="false" size="small"> 連接已斷開 </n-alert>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { NBadge, NAvatar, NAlert, useMessage } from 'naive-ui'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import SkeletonListItem from '@/components/ui/SkeletonListItem.vue'
import Icon from '@/components/ui/Icon.vue'
import { safeFormatDate } from '@/utils/dateFormat'
import { logger } from '@/utils/logger'

const router = useRouter()
const message = useMessage()
const chatStore = useChatStore()
const userStore = useUserStore()
const wsStore = useWebSocketStore()

const defaultAvatar = '/default-avatar.svg'

// 前往探索頁面
const goToDiscovery = () => {
  router.push('/discovery')
}

// 開啟聊天視窗
const openChat = (matchId) => {
  router.push(`/messages/${matchId}`)
}

// 格式化時間
// 使用共享的工具函數
const formatTime = safeFormatDate

// 獲取訊息預覽
const getMessagePreview = (message) => {
  if (!message) return ''

  const isOwn = message.sender_id === userStore.user?.id
  const prefix = isOwn ? '你: ' : ''

  // 處理圖片訊息
  if (message.message_type === 'IMAGE') {
    return prefix + '[圖片]'
  }

  // 處理 GIF 訊息
  if (message.message_type === 'GIF') {
    return prefix + '[GIF]'
  }

  // 處理文字訊息
  const maxLength = 50
  const content = message.content || ''

  if (content.length > maxLength) {
    return prefix + content.substring(0, maxLength) + '...'
  }

  return prefix + content
}

onMounted(async () => {
  try {
    // 載入對話列表
    // WebSocket 由 App.vue 統一管理，這裡不需要初始化
    await chatStore.fetchConversations()
  } catch (error) {
    message.error('載入對話列表失敗')
    logger.error('載入對話列表失敗:', error)
  }
})

onUnmounted(() => {
  // 組件卸載時清理 WebSocket (但不完全斷開，因為可能還有其他組件需要使用)
  // 如果需要完全斷開，可以調用 chatStore.closeWebSocket()
  // 這裡我們保持連接，只是清理本地狀態
})
</script>

<style scoped>
.chat-list-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%);
}

/* 載入中 - Skeleton */
.loading-skeleton {
  padding: var(--space-5);
}

.skeleton-list {
  display: flex;
  flex-direction: column;
}

/* 返回主選單按鈕 */
.back-home-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.95);
  color: #667eea;
  text-decoration: none;
  border-radius: 25px;
  font-weight: 600;
  font-size: 0.95rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.back-home-btn:hover {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: white;
  border-bottom: 2px solid #f0f0f0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 800;
  margin: 0;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  flex: 1;
  text-align: center;
}

/* 右側佔位符（與左側返回按鈕對稱） */
.header-spacer {
  width: 120px;
  flex-shrink: 0;
}

.chat-list-container {
  min-height: calc(100vh - 80px);
  padding: 20px;
}

/* 空狀態 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  text-align: center;
  background: white;
  border-radius: 20px;
  padding: 60px 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  animation: fadeIn 0.6s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.empty-animation {
  margin-bottom: 32px;
}

.empty-chat {
  display: inline-block;
  font-size: 6rem;
  animation: float 3s ease-in-out infinite;
  filter: drop-shadow(0 8px 16px rgba(102, 126, 234, 0.3));
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

.empty-state h2 {
  font-size: 2rem;
  font-weight: 800;
  color: #333;
  margin: 0 0 16px;
}

.empty-state p {
  font-size: 1.1rem;
  color: #666;
  margin: 0 0 32px;
  font-weight: 500;
}

.conversation-list {
  background: white;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 18px 24px;
  gap: 16px;
  cursor: pointer;
  border-bottom: 2px solid #f0f0f0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.conversation-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  transform: scaleY(0);
  transition: transform 0.3s ease;
}

.conversation-item:hover::before {
  transform: scaleY(1);
}

.conversation-item:hover {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.05), transparent);
  transform: translateX(4px);
}

.conversation-item:active {
  transform: translateX(2px);
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.08), transparent);
}

.avatar-badge {
  flex-shrink: 0;
}

.conversation-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.conversation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.user-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-time {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
  font-weight: 600;
}

.conversation-preview {
  display: flex;
  align-items: center;
}

.last-message {
  font-size: 0.95rem;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.last-message.unread {
  color: #333;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.no-message {
  font-size: 0.95rem;
  color: var(--color-text-muted);
  font-style: italic;
  font-weight: 500;
}

.arrow-icon {
  flex-shrink: 0;
  color: #ccc;
  transition: all 0.3s ease;
}

.conversation-item:hover .arrow-icon {
  color: #667eea;
  transform: translateX(4px);
}

.connection-warning {
  position: fixed;
  top: 90px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  width: 90%;
  max-width: 450px;
  animation: slideDown 0.4s ease;
}

@keyframes slideDown {
  from {
    transform: translateX(-50%) translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
  }
}

/* 響應式設計 */
@media (max-width: 768px) {
  .page-header {
    padding: 16px;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .chat-list-container {
    padding: 16px;
  }

  .empty-state {
    padding: 40px 24px;
    min-height: 400px;
  }

  .empty-chat {
    font-size: 5rem;
  }

  .empty-state h2 {
    font-size: 1.75rem;
  }

  .empty-state p {
    font-size: 1rem;
  }

  .conversation-item {
    padding: 16px 18px;
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .chat-list-page {
    background: white;
  }

  .page-header {
    padding: 12px;
    border-radius: 0;
  }

  .page-title {
    font-size: 1.3rem;
  }

  .back-home-btn {
    padding: 8px 14px;
    font-size: 0.85rem;
  }

  .chat-list-container {
    padding: 12px;
  }

  .empty-state {
    padding: 32px 20px;
    border-radius: 16px;
  }

  .empty-chat {
    font-size: 4rem;
  }

  .empty-state h2 {
    font-size: 1.5rem;
  }

  .conversation-list {
    border-radius: 16px;
  }

  .conversation-item {
    padding: 14px 16px;
  }

  .user-name {
    font-size: 1rem;
  }

  .last-message,
  .no-message {
    font-size: 0.9rem;
  }
}
</style>
