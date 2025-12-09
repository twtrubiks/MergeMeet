/**
 * Chat Store
 * 管理聊天相關狀態和 API 呼叫
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api/client'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from './user'
import { logger } from '@/utils/logger'

export const useChatStore = defineStore('chat', () => {
  // WebSocket instance
  const ws = useWebSocket()

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
    if (!currentMatchId.value) {
      console.log('🔥 [DEBUG] isTyping: false (no currentMatchId)')
      return false
    }
    const result = !!typingUsers.value[currentMatchId.value]
    console.log('🔥 [DEBUG] isTyping computed:', {
      currentMatchId: currentMatchId.value,
      typingUsers: typingUsers.value,
      result: result
    })
    return result
  })

  /**
   * 初始化 WebSocket 連接和訊息處理器
   * @returns {Promise<void>} 當 WebSocket 連接成功時 resolve
   */
  const initWebSocket = () => {
    // 註冊訊息處理器（在連接前註冊）
    ws.onMessage('new_message', handleNewMessage)
    ws.onMessage('typing', handleTypingIndicator)
    ws.onMessage('read_receipt', handleReadReceipt)
    ws.onMessage('message_deleted', handleMessageDeleted)

    // 連接 WebSocket
    return ws.connect()
  }

  /**
   * 關閉 WebSocket 連接
   */
  const closeWebSocket = () => {
    ws.disconnect()
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
   * 獲取聊天記錄
   */
  const fetchChatHistory = async (matchId, page = 1, pageSize = 50) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get(`/messages/matches/${matchId}/messages`, {
        params: { page, page_size: pageSize }
      })

      // 合併訊息 (避免重複)
      if (!messages.value[matchId]) {
        messages.value[matchId] = []
      }

      const existingIds = new Set(messages.value[matchId].map(m => m.id))
      const newMessages = response.data.messages.filter(m => !existingIds.has(m.id))

      // 按時間排序 (舊的在前)
      messages.value[matchId] = [...messages.value[matchId], ...newMessages].sort(
        (a, b) => new Date(a.sent_at) - new Date(b.sent_at)
      )

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
      // 透過 WebSocket 發送
      const success = ws.sendChatMessage(matchId, content, messageType)

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
   * 標記訊息為已讀
   */
  const markAsRead = async (messageIds) => {
    if (!messageIds || messageIds.length === 0) {
      return
    }

    try {
      await apiClient.post('/messages/messages/read', {
        message_ids: messageIds
      })

      // 更新本地狀態
      messageIds.forEach(msgId => {
        // 發送已讀回條
        ws.sendReadReceipt(msgId)
      })
    } catch (err) {
      logger.error('標記訊息為已讀失敗:', err)
    }
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
   * 發送打字指示器
   */
  const sendTyping = (matchId, isTyping) => {
    ws.sendTypingIndicator(matchId, isTyping)
  }

  /**
   * 加入配對聊天室
   */
  const joinMatchRoom = async (matchId) => {
    console.log('🔥 [DEBUG] Joining match room:', matchId)
    currentMatchId.value = matchId
    console.log('🔥 [DEBUG] currentMatchId set to:', currentMatchId.value)
    const joinResult = ws.joinMatch(matchId)
    console.log('🔥 [DEBUG] Join match result:', joinResult)

    // 獲取聊天記錄
    if (!messages.value[matchId]) {
      await fetchChatHistory(matchId)
    }

    // 標記已讀（確保訊息已載入後再執行）
    await markConversationAsRead(matchId)
  }

  /**
   * 離開配對聊天室
   */
  const leaveMatchRoom = () => {
    if (currentMatchId.value) {
      ws.leaveMatch(currentMatchId.value)
      currentMatchId.value = null
    }
  }

  /**
   * 處理新訊息事件
   */
  const handleNewMessage = (data) => {
    const message = data.message
    const matchId = message.match_id

    logger.debug('[Chat] Received new message:', { matchId, messageId: message.id })

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

      // 如果不是當前用戶發送的，增加未讀計數
      if (message.sender_id !== currentUserId() && matchId !== currentMatchId.value) {
        conv.unread_count = (conv.unread_count || 0) + 1
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
    console.log('🔥 [DEBUG] Typing indicator received:', data)
    logger.debug('[Chat] Received typing indicator:', data)
    const { match_id, user_id, is_typing } = data

    console.log('🔥 [DEBUG] Current matchId:', currentMatchId.value)
    console.log('🔥 [DEBUG] Typing users before:', typingUsers.value)

    if (is_typing) {
      // 使用 spread operator 創建新物件以觸發 Vue 響應式更新
      typingUsers.value = { ...typingUsers.value, [match_id]: user_id }
      console.log('🔥 [DEBUG] Typing users after (typing):', typingUsers.value)
      logger.debug('[Chat] User typing:', { match_id, user_id, typingUsers: typingUsers.value })
      // 3 秒後自動清除
      setTimeout(() => {
        if (typingUsers.value[match_id] === user_id) {
          // 使用解構移除屬性並創建新物件
          const { [match_id]: _, ...rest } = typingUsers.value
          typingUsers.value = rest
          console.log('🔥 [DEBUG] Typing timeout cleared')
          logger.debug('[Chat] Typing timeout cleared:', { match_id, user_id })
        }
      }, 3000)
    } else {
      // 使用解構移除屬性並創建新物件
      const { [match_id]: _, ...rest } = typingUsers.value
      typingUsers.value = rest
      console.log('🔥 [DEBUG] Typing stopped')
      logger.debug('[Chat] Typing stopped:', { match_id, user_id })
    }
  }

  /**
   * 處理已讀回條
   */
  const handleReadReceipt = (data) => {
    console.log('🔥 [DEBUG] Read receipt received:', data)
    const { message_id, read_at } = data

    // 更新訊息狀態（使用 map 創建新陣列觸發 Vue 響應式）
    for (const matchId in messages.value) {
      const messageIndex = messages.value[matchId].findIndex(m => m.id === message_id)
      if (messageIndex > -1) {
        console.log('🔥 [DEBUG] Updating message is_read:', message_id)
        // 創建新陣列以觸發 Vue 響應式更新
        messages.value[matchId] = messages.value[matchId].map((m, index) =>
          index === messageIndex ? { ...m, is_read: read_at } : m
        )
        console.log('🔥 [DEBUG] Message updated, new is_read:', messages.value[matchId][messageIndex].is_read)
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
    closeWebSocket()
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

    // WebSocket
    ws,
    initWebSocket,
    closeWebSocket,

    // Actions
    fetchConversations,
    fetchChatHistory,
    sendMessage,
    markAsRead,
    markConversationAsRead,
    deleteMessage,
    sendTyping,
    joinMatchRoom,
    leaveMatchRoom,
    clearError,
    $reset
  }
})
