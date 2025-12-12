<!--
  NotificationBell.vue
  通知鈴鐺組件 - 下拉式通知列表

  ========== 實作三種通知類型 ==========
  1. notification_message - 新訊息通知（顯示訊息圖示）
  2. notification_match - 新配對通知（顯示愛心圖示）
  3. notification_liked - 有人喜歡你通知（顯示人物圖示）
  ========================================
-->
<template>
  <n-popover
    trigger="click"
    placement="bottom-end"
    :show="showDropdown"
    @update:show="showDropdown = $event"
    :style="{ maxWidth: '360px' }"
  >
    <template #trigger>
      <n-badge
        :value="notificationStore.unreadCount"
        :max="99"
        :show="notificationStore.unreadCount > 0"
      >
        <n-button text class="bell-button">
          <template #icon>
            <n-icon size="24"><Notifications /></n-icon>
          </template>
        </n-button>
      </n-badge>
    </template>

    <div class="notification-dropdown">
      <!-- 標題列 -->
      <div class="notification-header">
        <span class="header-title">通知</span>
        <n-button
          text
          size="small"
          @click="markAllRead"
          v-if="notificationStore.unreadCount > 0"
          class="mark-all-btn"
        >
          全部已讀
        </n-button>
      </div>

      <!-- 通知列表 -->
      <div class="notification-list">
        <!-- 空狀態 -->
        <div v-if="notificationStore.recentNotifications.length === 0" class="empty-state">
          <n-icon size="48" :depth="3"><NotificationsOff /></n-icon>
          <span>暫無通知</span>
        </div>

        <!-- 通知項目 -->
        <div
          v-for="notification in notificationStore.recentNotifications"
          :key="notification.id"
          class="notification-item"
          :class="{ unread: !notification.read }"
          @click="handleNotificationClick(notification)"
        >
          <!-- 通知圖示 -->
          <div class="notification-icon" :class="getIconClass(notification.type)">
            <n-icon size="20">
              <component :is="getNotificationIconComponent(notification.type)" />
            </n-icon>
          </div>

          <!-- 通知內容 -->
          <div class="notification-content">
            <div class="notification-title">{{ notification.title }}</div>
            <div class="notification-preview">{{ notification.content }}</div>
            <div class="notification-time">{{ formatTime(notification.createdAt) }}</div>
          </div>

          <!-- 未讀指示點 -->
          <div v-if="!notification.read" class="unread-dot"></div>
        </div>
      </div>
    </div>
  </n-popover>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NPopover, NBadge, NButton, NIcon } from 'naive-ui'
import {
  Notifications,
  NotificationsOff,
  Heart,
  ChatbubbleEllipses,
  PersonAdd
} from '@vicons/ionicons5'
import { useNotificationStore, NotificationType } from '@/stores/notification'

const router = useRouter()
const notificationStore = useNotificationStore()

// State
const showDropdown = ref(false)

/**
 * 取得通知圖示組件
 * @param {string} type - 通知類型
 * @returns {Component} Vue 組件
 */
const getNotificationIconComponent = (type) => {
  switch (type) {
    case NotificationType.NEW_MESSAGE:
      // 【通知類型 1】新訊息 - 聊天氣泡圖示
      return ChatbubbleEllipses
    case NotificationType.NEW_MATCH:
      // 【通知類型 2】新配對 - 愛心圖示
      return Heart
    case NotificationType.SOMEONE_LIKED_YOU:
      // 【通知類型 3】有人喜歡你 - 人物圖示
      return PersonAdd
    default:
      return Notifications
  }
}

/**
 * 取得圖示樣式類別
 * @param {string} type - 通知類型
 * @returns {string} CSS 類別
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
 * 處理通知點擊
 * @param {object} notification - 通知物件
 */
const handleNotificationClick = (notification) => {
  // 標記為已讀
  notificationStore.markAsRead(notification.id)

  // 關閉下拉選單
  showDropdown.value = false

  // 根據通知類型導航到對應頁面
  switch (notification.type) {
    case NotificationType.NEW_MESSAGE:
      // 【通知類型 1】新訊息 → 導航到聊天頁面
      if (notification.data?.matchId) {
        router.push(`/messages/${notification.data.matchId}`)
      } else {
        router.push('/messages')
      }
      break

    case NotificationType.NEW_MATCH:
      // 【通知類型 2】新配對 → 導航到聊天頁面（開始對話）
      if (notification.data?.matchId) {
        router.push(`/messages/${notification.data.matchId}`)
      } else {
        router.push('/matches')
      }
      break

    case NotificationType.SOMEONE_LIKED_YOU:
      // 【通知類型 3】有人喜歡你 → 導航到探索頁面
      router.push('/discovery')
      break

    default:
      router.push('/messages')
  }
}

/**
 * 標記全部已讀
 */
const markAllRead = () => {
  notificationStore.markAllAsRead()
}

/**
 * 格式化時間（相對時間）
 * @param {Date|string} timestamp - 時間戳
 * @returns {string} 格式化後的時間字串
 */
const formatTime = (timestamp) => {
  if (!timestamp) return ''

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) {
    return '剛剛'
  } else if (diffMins < 60) {
    return `${diffMins} 分鐘前`
  } else if (diffHours < 24) {
    return `${diffHours} 小時前`
  } else if (diffDays < 7) {
    return `${diffDays} 天前`
  } else {
    return date.toLocaleDateString('zh-TW')
  }
}
</script>

<style scoped>
.bell-button {
  color: #333;
}

.bell-button:hover {
  color: #ff6b6b;
}

.notification-dropdown {
  width: 320px;
  max-height: 400px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.header-title {
  font-weight: 600;
  font-size: 16px;
  color: #333;
}

.mark-all-btn {
  color: #ff6b6b;
  font-size: 13px;
}

.notification-list {
  overflow-y: auto;
  max-height: 340px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
  gap: 12px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  position: relative;
  border-bottom: 1px solid #f5f5f5;
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

.notification-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
}

/* 【通知類型 1】新訊息 - 藍色背景 */
.icon-message {
  background-color: #e3f2fd;
  color: #1976d2;
}

/* 【通知類型 2】新配對 - 粉色背景 */
.icon-match {
  background-color: #fce4ec;
  color: #e91e63;
}

/* 【通知類型 3】有人喜歡你 - 紫色背景 */
.icon-liked {
  background-color: #f3e5f5;
  color: #9c27b0;
}

.icon-default {
  background-color: #f5f5f5;
  color: #666;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 500;
  font-size: 14px;
  color: #333;
  margin-bottom: 4px;
  line-height: 1.3;
}

.notification-preview {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-time {
  font-size: 12px;
  color: #999;
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ff6b6b;
  flex-shrink: 0;
  margin-left: 8px;
  margin-top: 4px;
}
</style>
