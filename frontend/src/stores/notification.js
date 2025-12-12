/**
 * Notification Store
 * 管理即時通知狀態
 *
 * ========== 實作三種通知類型 ==========
 * 1. notification_message - 新訊息通知（接收者不在聊天室時）
 * 2. notification_match - 新配對通知（互相喜歡時）
 * 3. notification_liked - 有人喜歡你通知（單方喜歡時）
 * ========================================
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useWebSocketStore } from './websocket'
import { logger } from '@/utils/logger'

// 通知類型常量
export const NotificationType = {
  // 【通知類型 1】新訊息通知
  NEW_MESSAGE: 'notification_message',
  // 【通知類型 2】新配對通知
  NEW_MATCH: 'notification_match',
  // 【通知類型 3】有人喜歡你通知
  SOMEONE_LIKED_YOU: 'notification_liked'
}

export const useNotificationStore = defineStore('notification', () => {
  // State
  const notifications = ref([])  // 通知列表
  const loading = ref(false)

  // Getters
  /**
   * 未讀通知數量
   */
  const unreadCount = computed(() => {
    return notifications.value.filter(n => !n.read).length
  })

  /**
   * 最近通知（用於下拉列表顯示，最多 20 筆）
   */
  const recentNotifications = computed(() => {
    return notifications.value.slice(0, 20)
  })

  /**
   * 取得通知圖示類型（用於 UI 顯示）
   * @param {string} type - 通知類型
   * @returns {string} 圖示名稱
   */
  const getNotificationIcon = (type) => {
    switch (type) {
      case NotificationType.NEW_MESSAGE:
        return 'ChatbubbleEllipses'
      case NotificationType.NEW_MATCH:
        return 'Heart'
      case NotificationType.SOMEONE_LIKED_YOU:
        return 'PersonAdd'
      default:
        return 'Notifications'
    }
  }

  /**
   * 新增通知
   * @param {object} notification - 通知資料
   */
  const addNotification = (notification) => {
    const newNotification = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      ...notification,
      read: false,
      createdAt: new Date()
    }

    // 插入到列表開頭
    notifications.value.unshift(newNotification)

    // 限制通知數量（最多保留 100 筆）
    if (notifications.value.length > 100) {
      notifications.value = notifications.value.slice(0, 100)
    }

    logger.debug('[Notification] Added:', newNotification.type)
    return newNotification
  }

  /**
   * 【通知類型 1】處理新訊息通知
   * @param {object} data - WebSocket 訊息資料
   */
  const handleMessageNotification = (data) => {
    logger.debug('[Notification] Received notification_message:', data)

    addNotification({
      type: NotificationType.NEW_MESSAGE,
      title: `${data.sender_name} 發送了訊息`,
      content: data.preview || '新訊息',
      data: {
        matchId: data.match_id,
        senderId: data.sender_id
      },
      timestamp: data.timestamp
    })

    // 同時更新 ChatList 的未讀計數（延遲 import 避免循環依賴）
    import('./chat').then(({ useChatStore }) => {
      const chatStore = useChatStore()
      const conv = chatStore.conversations.find(c => c.match_id === data.match_id)
      if (conv) {
        conv.unread_count = (conv.unread_count || 0) + 1
        conv.last_message = {
          content: data.preview,
          sent_at: data.timestamp,
          sender_id: data.sender_id
        }
        // 將對話移到列表頂部
        chatStore.conversations = [
          conv,
          ...chatStore.conversations.filter(c => c.match_id !== data.match_id)
        ]
        logger.debug('[Notification] Updated conversation unread_count:', conv.unread_count)
      }
    })
  }

  /**
   * 【通知類型 2】處理新配對通知
   * @param {object} data - WebSocket 訊息資料
   */
  const handleMatchNotification = (data) => {
    logger.debug('[Notification] Received notification_match:', data)

    addNotification({
      type: NotificationType.NEW_MATCH,
      title: '恭喜！你有新配對',
      content: `你和 ${data.matched_user_name} 互相喜歡！`,
      data: {
        matchId: data.match_id,
        userId: data.matched_user_id,
        userName: data.matched_user_name,
        userAvatar: data.matched_user_avatar
      },
      timestamp: data.timestamp
    })
  }

  /**
   * 【通知類型 3】處理有人喜歡你通知
   * @param {object} data - WebSocket 訊息資料
   */
  const handleLikedNotification = (data) => {
    logger.debug('[Notification] Received notification_liked:', data)

    addNotification({
      type: NotificationType.SOMEONE_LIKED_YOU,
      title: '有人喜歡你',
      content: '有人對你表示好感，快去探索看看吧！',
      data: {},  // 不透露是誰喜歡，保持神秘感
      timestamp: data.timestamp
    })
  }

  /**
   * 初始化通知監聽器
   * 註冊 WebSocket 訊息處理器
   * @returns {function} 取消註冊函數
   */
  const initNotificationListeners = () => {
    const wsStore = useWebSocketStore()

    // 註冊三種通知類型的處理器
    const unsubscribers = [
      // 【通知類型 1】新訊息通知
      wsStore.onMessage('notification_message', handleMessageNotification),
      // 【通知類型 2】新配對通知
      wsStore.onMessage('notification_match', handleMatchNotification),
      // 【通知類型 3】有人喜歡你通知
      wsStore.onMessage('notification_liked', handleLikedNotification)
    ]

    logger.log('[Notification] Listeners initialized for 3 notification types')

    // 返回取消註冊函數
    return () => {
      unsubscribers.forEach(unsub => unsub())
      logger.log('[Notification] Listeners unregistered')
    }
  }

  /**
   * 標記單個通知為已讀
   * @param {string} notificationId - 通知 ID
   */
  const markAsRead = (notificationId) => {
    const notification = notifications.value.find(n => n.id === notificationId)
    if (notification && !notification.read) {
      notification.read = true
      logger.debug('[Notification] Marked as read:', notificationId)
    }
  }

  /**
   * 標記所有通知為已讀
   */
  const markAllAsRead = () => {
    let count = 0
    notifications.value.forEach(n => {
      if (!n.read) {
        n.read = true
        count++
      }
    })
    logger.debug('[Notification] Marked all as read:', count)
  }

  /**
   * 移除單個通知
   * @param {string} notificationId - 通知 ID
   */
  const removeNotification = (notificationId) => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index > -1) {
      notifications.value.splice(index, 1)
      logger.debug('[Notification] Removed:', notificationId)
    }
  }

  /**
   * 清空所有通知
   */
  const clearAll = () => {
    notifications.value = []
    logger.debug('[Notification] Cleared all')
  }

  /**
   * 重置 Store
   */
  const $reset = () => {
    notifications.value = []
    loading.value = false
  }

  return {
    // State
    notifications,
    loading,

    // Getters
    unreadCount,
    recentNotifications,

    // Methods
    getNotificationIcon,
    addNotification,
    initNotificationListeners,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    $reset,

    // Constants
    NotificationType
  }
})
