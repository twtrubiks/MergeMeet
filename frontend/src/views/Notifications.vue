<template>
  <div class="notifications-page">
    <div class="container">
      <!-- 返回按鈕 -->
      <router-link to="/" class="back-btn">
        <span class="btn-icon">←</span>
        <span class="btn-text">返回</span>
      </router-link>

      <h1 class="page-title">通知中心</h1>

      <!-- 操作欄 -->
      <div v-if="notificationStore.unreadCount > 0" class="action-bar">
        <button
          class="mark-all-btn"
          @click="handleMarkAllRead"
          :disabled="markingAllRead"
        >
          {{ markingAllRead ? '處理中...' : '全部標記已讀' }}
        </button>
      </div>

      <!-- 載入中 -->
      <div v-if="loading && notifications.length === 0" class="loading-state">
        <div class="spinner"></div>
        <p>載入中...</p>
      </div>

      <!-- 空狀態 -->
      <div v-else-if="notifications.length === 0" class="empty-state">
        <div class="empty-icon">🔔</div>
        <h2>暫無通知</h2>
        <p>當有新消息時，會在這裡顯示</p>
      </div>

      <!-- 通知列表 -->
      <div v-else class="notification-list">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          class="notification-item"
          :class="{ unread: !notification.read }"
          @click="handleNotificationClick(notification)"
        >
          <!-- 通知圖示 -->
          <div class="notification-icon" :class="getIconClass(notification.type)">
            {{ getIconEmoji(notification.type) }}
          </div>

          <!-- 通知內容 -->
          <div class="notification-content">
            <div class="notification-title">{{ notification.title }}</div>
            <div class="notification-body">{{ notification.content }}</div>
            <div class="notification-time">{{ formatTime(notification.createdAt) }}</div>
          </div>

          <!-- 操作按鈕 -->
          <div class="notification-actions">
            <button
              class="delete-btn"
              @click.stop="handleDelete(notification.id)"
              title="刪除"
            >
              🗑️
            </button>
          </div>

          <!-- 未讀指示點 -->
          <div v-if="!notification.read" class="unread-dot"></div>
        </div>

        <!-- 載入更多 -->
        <div v-if="hasMore" class="load-more">
          <button
            class="load-more-btn"
            @click="loadMore"
            :disabled="loadingMore"
          >
            {{ loadingMore ? '載入中...' : '載入更多' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore, NotificationType } from '@/stores/notification'
import { logger } from '@/utils/logger'

const router = useRouter()
const notificationStore = useNotificationStore()

// State
const loading = ref(false)
const loadingMore = ref(false)
const markingAllRead = ref(false)
const currentPage = ref(0)
const pageSize = 20
const hasMore = ref(true)
const totalCount = ref(0)

// Computed
const notifications = computed(() => notificationStore.notifications)

/**
 * 取得通知圖示 emoji
 * @param {string} type - 通知類型
 */
const getIconEmoji = (type) => {
  switch (type) {
    case NotificationType.NEW_MESSAGE:
      return '💬'
    case NotificationType.NEW_MATCH:
      return '💕'
    case NotificationType.SOMEONE_LIKED_YOU:
      return '👤'
    default:
      return '🔔'
  }
}

/**
 * 取得圖示樣式類別
 * @param {string} type - 通知類型
 */
const getIconClass = (type) => {
  switch (type) {
    case NotificationType.NEW_MESSAGE:
      return 'icon-message'
    case NotificationType.NEW_MATCH:
      return 'icon-match'
    case NotificationType.SOMEONE_LIKED_YOU:
      return 'icon-liked'
    default:
      return 'icon-default'
  }
}

/**
 * 格式化時間
 * @param {Date|string} timestamp - 時間戳
 */
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
  return date.toLocaleDateString('zh-TW')
}

/**
 * 載入通知
 * @param {boolean} isLoadMore - 是否為載入更多
 */
const loadNotifications = async (isLoadMore = false) => {
  if (isLoadMore) {
    loadingMore.value = true
  } else {
    loading.value = true
  }

  try {
    const result = await notificationStore.fetchNotifications({
      limit: pageSize,
      offset: currentPage.value * pageSize
    })

    totalCount.value = result.total || 0
    hasMore.value = result.notifications.length === pageSize

    logger.debug('[Notifications] Loaded:', result.notifications.length)
  } catch (error) {
    logger.error('[Notifications] Failed to load:', error)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

/**
 * 載入更多
 */
const loadMore = async () => {
  currentPage.value++
  await loadNotifications(true)
}

/**
 * 點擊通知
 * @param {object} notification - 通知物件
 */
const handleNotificationClick = async (notification) => {
  // 標記為已讀
  if (!notification.read) {
    try {
      if (notification.fromAPI) {
        await notificationStore.markAsReadAPI(notification.id)
      } else {
        notificationStore.markAsRead(notification.id)
      }
    } catch (error) {
      logger.error('[Notifications] Failed to mark as read:', error)
    }
  }

  // 根據通知類型導航
  const matchId = notification.data?.matchId || notification.data?.match_id

  switch (notification.type) {
    case NotificationType.NEW_MESSAGE:
      if (matchId) {
        router.push(`/messages/${matchId}`)
      } else {
        router.push('/messages')
      }
      break

    case NotificationType.NEW_MATCH:
      if (matchId) {
        router.push(`/messages/${matchId}`)
      } else {
        router.push('/matches')
      }
      break

    case NotificationType.SOMEONE_LIKED_YOU:
      router.push('/discovery')
      break

    default:
      router.push('/messages')
  }
}

/**
 * 全部標記已讀
 */
const handleMarkAllRead = async () => {
  markingAllRead.value = true
  try {
    await notificationStore.markAllAsReadAPI()
    logger.debug('[Notifications] Marked all as read')
  } catch (error) {
    logger.error('[Notifications] Failed to mark all as read:', error)
  } finally {
    markingAllRead.value = false
  }
}

/**
 * 刪除通知
 * @param {string} notificationId - 通知 ID
 */
const handleDelete = async (notificationId) => {
  try {
    await notificationStore.deleteNotificationAPI(notificationId)
    logger.debug('[Notifications] Deleted:', notificationId)
  } catch (error) {
    logger.error('[Notifications] Failed to delete:', error)
  }
}

// Lifecycle
onMounted(() => {
  loadNotifications()
})
</script>

<style scoped>
.notifications-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #FFF5F5 0%, #FFE5E5 100%);
  padding: 20px;
}

.container {
  max-width: 600px;
  margin: 0 auto;
}

/* 返回按鈕 */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.95);
  color: #FF6B6B;
  text-decoration: none;
  border-radius: 25px;
  font-weight: 600;
  font-size: 0.95rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  margin-bottom: 15px;
}

.back-btn:hover {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.3);
}

.back-btn .btn-icon {
  font-size: 1.2rem;
}

.page-title {
  text-align: center;
  font-size: 32px;
  font-weight: 700;
  color: #333;
  margin-bottom: 20px;
}

/* 操作欄 */
.action-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.mark-all-btn {
  padding: 10px 20px;
  background: #FF6B6B;
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.mark-all-btn:hover:not(:disabled) {
  background: #FF5252;
  transform: translateY(-2px);
}

.mark-all-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 載入狀態 */
.loading-state {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #FF6B6B;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h2 {
  font-size: 20px;
  color: #333;
  margin: 0 0 8px;
}

.empty-state p {
  font-size: 14px;
  color: #999;
  margin: 0;
}

/* 通知列表 */
.notification-list {
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  padding: 16px 20px;
  cursor: pointer;
  transition: background-color 0.2s;
  position: relative;
  border-bottom: 1px solid #f5f5f5;
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-item:hover {
  background-color: #f8f9fa;
}

.notification-item.unread {
  background-color: #fff8f8;
}

.notification-item.unread:hover {
  background-color: #fff0f0;
}

/* 通知圖示 */
.notification-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  flex-shrink: 0;
  font-size: 24px;
}

.icon-message {
  background-color: #e3f2fd;
}

.icon-match {
  background-color: #fce4ec;
}

.icon-liked {
  background-color: #f3e5f5;
}

.icon-default {
  background-color: #f5f5f5;
}

/* 通知內容 */
.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 600;
  font-size: 15px;
  color: #333;
  margin-bottom: 4px;
}

.notification-body {
  font-size: 14px;
  color: #666;
  margin-bottom: 6px;
  line-height: 1.4;
}

.notification-time {
  font-size: 12px;
  color: #999;
}

/* 操作按鈕 */
.notification-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 12px;
}

.delete-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.delete-btn:hover {
  background-color: #ffebee;
}

/* 未讀指示點 */
.unread-dot {
  position: absolute;
  top: 20px;
  right: 16px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #FF6B6B;
}

/* 載入更多 */
.load-more {
  padding: 16px;
  text-align: center;
  border-top: 1px solid #f5f5f5;
}

.load-more-btn {
  padding: 10px 30px;
  background: transparent;
  color: #FF6B6B;
  border: 2px solid #FF6B6B;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.load-more-btn:hover:not(:disabled) {
  background: #FF6B6B;
  color: white;
}

.load-more-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .notification-item {
    padding: 12px 16px;
  }

  .notification-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
    margin-right: 12px;
  }

  .notification-title {
    font-size: 14px;
  }

  .notification-body {
    font-size: 13px;
  }
}
</style>
