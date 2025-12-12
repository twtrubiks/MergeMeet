/**
 * Chat Store
 * 管理聊天相關狀態和 API 呼叫
 *
 * 重構說明：
 * - 移除內部 WebSocket 實例，改用全域 WebSocketStore
 * - WebSocket 連接由 App.vue 統一管理
 * - 本 Store 只負責聊天業務邏輯和訊息處理器註冊
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api/client'
import { useWebSocketStore } from './websocket'
import { useUserStore } from './user'
import { logger } from '@/utils/logger'

export const useChatStore = defineStore('chat', () => {
  // 使用全域 WebSocket Store（不再自己創建實例）
  const wsStore = useWebSocketStore()

  // State
  const conversations = ref([]) // 對話列表
  const messages = ref({}) // matchId -> messages array
  const currentMatchId = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const typingUsers = ref({}) // matchId -> userId (正在打字的用戶)

  // Getters
  const currentConversation = computed(() => {
    return conversations.value.find(c => c.match_id === currentMatchId.value)
  })

  const currentMessages = computed(() => {
    if (!currentMatchId.value) return []
    return messages.value[currentMatchId.value] || []
  })

  const unreadCount = computed(() => {
    return conversations.value.reduce((sum, conv) => sum + conv.unread_count, 0)
  })

  const isTyping = computed(() => {
    if (!currentMatchId.value) return false
    return !!typingUsers.value[currentMatchId.value]
  })

  /**
   * 初始化聊天訊息處理器
   *
   * 重構說明：
   * - 不再負責 WebSocket 連接（由 App.vue 統一管理）
   * - 只負責註冊聊天相關的訊息處理器
   * - 返回取消註冊函數，供組件卸載時調用
   *
   * @returns {function} 取消註冊所有處理器的函數
   */
  const initChatHandlers = () => {
    // 註冊訊息處理器
    const unsubscribers = [
      wsStore.onMessage('new_message', handleNewMessage),
      wsStore.onMessage('typing', handleTypingIndicator),
      wsStore.onMessage('read_receipt', handleReadReceipt),
      wsStore.onMessage('message_deleted', handleMessageDeleted)
    ]

    logger.debug('[ChatStore] Chat handlers registered')

    // 返回取消註冊函數
    return () => {
      unsubscribers.forEach(unsub => unsub())
      logger.debug('[ChatStore] Chat handlers unregistered')
    }
  }

  /**
   * 初始化 WebSocket 連接和訊息處理器（保留向後兼容）
   * @deprecated 使用 initChatHandlers() 代替
   * @returns {Promise<void>}
   */
  const initWebSocket = () => {
    initChatHandlers()
    // WebSocket 連接由全域 Store 管理，這裡只等待連接
    return wsStore.connect()
  }

  /**
   * 關閉 WebSocket 連接（保留向後兼容）
   * @deprecated WebSocket 連接由 App.vue 統一管理
   */
  const closeWebSocket = () => {
    // 不再由 Chat Store 管理 WebSocket 連接
    logger.debug('[ChatStore] closeWebSocket called (no-op, managed by App.vue)')
  }

  /**
   * 獲取對話列表
   */
  const fetchConversations = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/messages/conversations')
      conversations.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '無法取得對話列表'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 獲取聊天記錄 (Cursor-based pagination)
   *
   * @param {string} matchId - 配對 ID
   * @param {string|null} beforeId - Cursor: 載入比此訊息 ID 更早的訊息
   * @param {number} limit - 每次載入數量
   * @returns {Promise<Object>} API 回應 (含 messages, has_more, next_cursor, total)
   *
   * 使用方式：
   * - 初次載入：fetchChatHistory(matchId) - 取最新 50 條
   * - 載入更多：fetchChatHistory(matchId, next_cursor) - 取更早的訊息
   */
  const fetchChatHistory = async (matchId, beforeId = null, limit = 50) => {
    loading.value = true
    error.value = null
    try {
      const params = { limit }
      if (beforeId) {
        params.before_id = beforeId
      }

      const response = await apiClient.get(`/messages/matches/${matchId}/messages`, {
        params
      })

      if (beforeId) {
        // 載入更多歷史訊息：將歷史訊息插入到開頭
        // response.data.messages 是正序（舊的在前）
        const existingMessages = messages.value[matchId] || []
        messages.value[matchId] = [
          ...response.data.messages,
          ...existingMessages
        ]
      } else {
        // 初次載入：直接覆蓋（API 是權威來源）
        messages.value[matchId] = response.data.messages
      }

      logger.debug('[Chat] Fetched messages:', {
        matchId,
        beforeId,
        count: response.data.messages.length,
        hasMore: response.data.has_more,
        nextCursor: response.data.next_cursor
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '無法取得聊天記錄'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 發送訊息
   */
  const sendMessage = async (matchId, content, messageType = 'TEXT') => {
    if (!content.trim()) {
      return
    }

    try {
      // 透過全域 WebSocket Store 發送
      const success = wsStore.sendChatMessage(matchId, content, messageType)

      if (!success) {
        throw new Error('WebSocket 未連接')
      }

      // 訊息會透過 WebSocket 的 new_message 事件返回並加入到列表中
    } catch (err) {
      error.value = err.message || '發送訊息失敗'
      throw err
    }
  }

  /**
   * 標記訊息為已讀（使用 WebSocket 即時處理）
   *
   * 重構說明：
   * - 改為只用 WebSocket 處理已讀回條（業界標準做法）
   * - WebSocket 即時性更好，適合聊天場景
   * - 避免 REST API 和 WebSocket 的重複處理和競爭條件
   * - 參考：WhatsApp、Telegram 都只用 WebSocket 處理即時已讀狀態
   */
  const markAsRead = async (messageIds) => {
    if (!messageIds || messageIds.length === 0) {
      return
    }

    // 只通過全域 WebSocket Store 發送已讀回條
    // 後端會標記資料庫並通知對方
    messageIds.forEach(msgId => {
      wsStore.sendReadReceipt(msgId)
    })

    logger.debug('[Chat] Sent read receipts via WebSocket:', messageIds)
  }

  /**
   * 標記對話中所有未讀訊息為已讀
   */
  const markConversationAsRead = async (matchId) => {
    if (!messages.value[matchId]) return

    const unreadMessages = messages.value[matchId]
      .filter(m => !m.is_read && m.sender_id !== currentUserId())
      .map(m => m.id)

    if (unreadMessages.length > 0) {
      await markAsRead(unreadMessages)

      // 更新對話列表中的未讀數
      const conv = conversations.value.find(c => c.match_id === matchId)
      if (conv) {
        conv.unread_count = 0
      }
    }
  }

  /**
   * 刪除訊息
   */
  const deleteMessage = async (messageId) => {
    try {
      await apiClient.delete(`/messages/messages/${messageId}`)

      // 從本地狀態移除
      for (const matchId in messages.value) {
        const index = messages.value[matchId].findIndex(m => m.id === messageId)
        if (index > -1) {
          messages.value[matchId].splice(index, 1)
          break
        }
      }
    } catch (err) {
      error.value = err.response?.data?.detail || '刪除訊息失敗'
      throw err
    }
  }

  /**
   * 上傳聊天圖片
   * @param {string} matchId - 配對 ID
   * @param {File} file - 圖片檔案
   * @returns {Promise<Object>} 上傳結果 (含 image_url, thumbnail_url, width, height, is_gif)
   */
  const uploadChatImage = async (matchId, file) => {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await apiClient.post(
        `/messages/matches/${matchId}/upload-image`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      )

      logger.debug('[Chat] Image uploaded:', response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '上傳圖片失敗'
      throw err
    }
  }

  /**
   * 發送圖片訊息
   * @param {string} matchId - 配對 ID
   * @param {Object} imageData - 圖片資料 (來自 uploadChatImage)
   */
  const sendImageMessage = async (matchId, imageData) => {
    const content = JSON.stringify({
      image_url: imageData.image_url,
      thumbnail_url: imageData.thumbnail_url,
      width: imageData.width,
      height: imageData.height
    })

    const messageType = imageData.is_gif ? 'GIF' : 'IMAGE'

    try {
      await sendMessage(matchId, content, messageType)
      logger.debug('[Chat] Image message sent:', { matchId, messageType })
    } catch (err) {
      error.value = err.message || '發送圖片訊息失敗'
      throw err
    }
  }

  /**
   * 發送打字指示器
   */
  const sendTyping = (matchId, isTyping) => {
    wsStore.sendTypingIndicator(matchId, isTyping)
  }

  /**
   * 加入配對聊天室
   * @returns {Promise<Object>} API 回應 (含 has_more, next_cursor 供前端分頁使用)
   */
  const joinMatchRoom = async (matchId) => {
    currentMatchId.value = matchId
    wsStore.joinMatch(matchId)

    // 每次進入聊天室都重新載入最新訊息
    // 這確保用戶能看到離開期間的新訊息
    const result = await fetchChatHistory(matchId)

    // 標記已讀（確保訊息已載入後再執行）
    await markConversationAsRead(matchId)

    // 返回結果供前端使用 cursor 資訊
    return result
  }

  /**
   * 離開配對聊天室
   */
  const leaveMatchRoom = () => {
    if (currentMatchId.value) {
      wsStore.leaveMatch(currentMatchId.value)
      currentMatchId.value = null
    }
  }

  /**
   * 處理新訊息事件
   */
  const handleNewMessage = async (data) => {
    const message = data.message
    const matchId = message.match_id

    logger.debug('[Chat] Received new message:', { matchId, messageId: message.id, messageType: message.message_type })

    // 確保該配對的訊息陣列存在，使用解構賦值確保響應式
    if (!messages.value[matchId]) {
      messages.value = {
        ...messages.value,
        [matchId]: []
      }
    }

    // 檢查是否已存在 (避免重複)
    const exists = messages.value[matchId].some(m => m.id === message.id)
    if (!exists) {
      // 使用解構賦值更新陣列，確保響應式更新
      messages.value[matchId] = [...messages.value[matchId], message]
      logger.debug('[Chat] Message added to store:', { matchId, totalMessages: messages.value[matchId].length })
    } else {
      logger.debug('[Chat] Message already exists, skipping')
    }

    // 更新對話列表中的最後一條訊息
    const conv = conversations.value.find(c => c.match_id === matchId)
    if (conv) {
      conv.last_message = message

      // 處理未讀計數和已讀標記
      if (message.sender_id !== currentUserId()) {
        // 如果在當前聊天室，立即標記為已讀
        if (matchId === currentMatchId.value) {
          // 立即標記這條訊息為已讀
          await markAsRead([message.id])
        } else {
          // 不在當前聊天室，增加未讀計數
          conv.unread_count = (conv.unread_count || 0) + 1
        }
      }

      // 將對話移到列表頂部
      conversations.value = [
        conv,
        ...conversations.value.filter(c => c.match_id !== matchId)
      ]
    }
  }

  /**
   * 處理打字指示器
   */
  const handleTypingIndicator = (data) => {
    logger.debug('[Chat] Received typing indicator:', data)
    const { match_id, user_id, is_typing } = data

    if (is_typing) {
      // 使用 spread operator 創建新物件以觸發 Vue 響應式更新
      typingUsers.value = { ...typingUsers.value, [match_id]: user_id }
      logger.debug('[Chat] User typing:', { match_id, user_id })
      // 3 秒後自動清除
      setTimeout(() => {
        if (typingUsers.value[match_id] === user_id) {
          // 使用解構移除屬性並創建新物件
          const { [match_id]: _, ...rest } = typingUsers.value
          typingUsers.value = rest
          logger.debug('[Chat] Typing timeout cleared')
        }
      }, 3000)
    } else {
      // 使用解構移除屬性並創建新物件
      const { [match_id]: _, ...rest } = typingUsers.value
      typingUsers.value = rest
      logger.debug('[Chat] Typing stopped')
    }
  }

  /**
   * 處理已讀回條
   */
  const handleReadReceipt = (data) => {
    logger.debug('[Chat] Received read receipt:', data)
    const { message_id, read_at } = data

    // 更新訊息狀態（使用 map 創建新陣列觸發 Vue 響應式）
    for (const matchId in messages.value) {
      const messageIndex = messages.value[matchId].findIndex(m => m.id === message_id)
      if (messageIndex > -1) {
        // 創建新陣列以觸發 Vue 響應式更新
        messages.value[matchId] = messages.value[matchId].map((m, index) =>
          index === messageIndex ? { ...m, is_read: read_at } : m
        )
        logger.debug('[Chat] Message marked as read:', message_id)
        break
      }
    }
  }

  /**
   * 處理訊息刪除事件（來自 WebSocket）
   */
  const handleMessageDeleted = (data) => {
    const { message_id, match_id } = data

    logger.debug('[Chat] Received message_deleted event:', data)

    // 從本地狀態移除訊息
    if (messages.value[match_id]) {
      const index = messages.value[match_id].findIndex(m => m.id === message_id)
      if (index > -1) {
        messages.value[match_id].splice(index, 1)
        logger.debug('[Chat] Message removed from local state:', message_id)
      }
    }
  }

  /**
   * 獲取當前用戶 ID (從 user store)
   */
  const currentUserId = () => {
    const userStore = useUserStore()
    return userStore.user?.id
  }

  /**
   * 清除錯誤訊息
   */
  const clearError = () => {
    error.value = null
  }

  /**
   * 重置 Store
   */
  const $reset = () => {
    conversations.value = []
    messages.value = {}
    currentMatchId.value = null
    loading.value = false
    error.value = null
    typingUsers.value = {}
    // 不再由 Chat Store 管理 WebSocket 連接
  }

  return {
    // State
    conversations,
    messages,
    currentMatchId,
    loading,
    error,
    typingUsers,

    // Getters
    currentConversation,
    currentMessages,
    unreadCount,
    isTyping,

    // WebSocket（全域 Store 參考）
    wsStore,
    initWebSocket,       // 保留向後兼容
    closeWebSocket,      // 保留向後兼容
    initChatHandlers,    // 新方法：只註冊訊息處理器

    // Actions
    fetchConversations,
    fetchChatHistory,
    sendMessage,
    markAsRead,
    markConversationAsRead,
    deleteMessage,
    uploadChatImage,
    sendImageMessage,
    sendTyping,
    joinMatchRoom,
    leaveMatchRoom,
    clearError,
    $reset
  }
})
