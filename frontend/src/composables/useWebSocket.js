/**
 * WebSocket Composable
 * 管理 WebSocket 連接和訊息處理
 */
import { ref, onUnmounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { logger } from '@/utils/logger'

// WebSocket 連接狀態
const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting'
}

export function useWebSocket() {
  const userStore = useUserStore()

  // State
  const socket = ref(null)
  const connectionState = ref(ConnectionState.DISCONNECTED)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000 // 3 秒
  const messageHandlers = ref(new Map())

  // Getters
  const isConnected = computed(() => connectionState.value === ConnectionState.CONNECTED)
  const isConnecting = computed(() =>
    connectionState.value === ConnectionState.CONNECTING ||
    connectionState.value === ConnectionState.RECONNECTING
  )

  /**
   * 建立 WebSocket 連接（使用首次訊息認證）
   *
   * 安全改進：Token 不再透過 URL 傳遞，而是在連接建立後通過首次訊息發送
   *
   * @returns {Promise<void>} 當連接成功並認證完成時 resolve
   */
  const connect = () => {
    if (socket.value?.readyState === WebSocket.OPEN) {
      logger.log('WebSocket already connected')
      return Promise.resolve()
    }

    if (!userStore.isAuthenticated || !userStore.user?.id) {
      logger.error('Cannot connect: User not authenticated')
      return Promise.reject(new Error('User not authenticated'))
    }

    connectionState.value = reconnectAttempts.value > 0
      ? ConnectionState.RECONNECTING
      : ConnectionState.CONNECTING

    return new Promise((resolve, reject) => {
      try {
        // 建立 WebSocket 連接（URL 中不包含 Token，避免洩漏）
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsHost = import.meta.env.VITE_WS_URL || 'localhost:8000'
        const token = userStore.accessToken
        const userId = userStore.user.id

        const wsUrl = `${wsProtocol}//${wsHost}/ws`

        socket.value = new WebSocket(wsUrl)

        // 連接成功後立即發送認證訊息
        socket.value.onopen = () => {
          logger.log('WebSocket connected, sending auth...')

          // 發送認證訊息（Token 安全地通過 WebSocket 訊息傳遞）
          socket.value.send(JSON.stringify({
            type: 'auth',
            token: token,
            user_id: userId
          }))

          // 等待認證成功回應
          const authTimeout = setTimeout(() => {
            logger.error('WebSocket authentication timeout')
            socket.value.close()
            reject(new Error('Authentication timeout'))
          }, 5000) // 5 秒超時

          // 暫存 onmessage 處理器以接收認證回應
          const tempMessageHandler = (event) => {
            try {
              const data = JSON.parse(event.data)

              if (data.type === 'auth_success') {
                clearTimeout(authTimeout)
                logger.log('WebSocket authenticated successfully')
                connectionState.value = ConnectionState.CONNECTED
                reconnectAttempts.value = 0

                // 移除臨時處理器，啟用正常訊息處理
                socket.value.onmessage = normalMessageHandler
                resolve()
              } else if (data.type === 'error' && data.message?.includes('auth')) {
                clearTimeout(authTimeout)
                logger.error('WebSocket authentication failed:', data.message)
                socket.value.close()
                reject(new Error('Authentication failed'))
              }
            } catch (error) {
              logger.error('Error parsing auth response:', error)
            }
          }

          socket.value.onmessage = tempMessageHandler
        }

        // 正常訊息處理器（認證成功後使用）
        const normalMessageHandler = (event) => {
          try {
            const data = JSON.parse(event.data)
            handleMessage(data)
          } catch (error) {
            logger.error('Error parsing WebSocket message:', error)
          }
        }

        // 連接關閉
        socket.value.onclose = (event) => {
          logger.log('WebSocket closed:', event.code, event.reason)
          connectionState.value = ConnectionState.DISCONNECTED
          socket.value = null

          // 嘗試重新連接 (除非是正常關閉)
          if (event.code !== 1000 && reconnectAttempts.value < maxReconnectAttempts) {
            scheduleReconnect()
          }
        }

        // 連接錯誤
        socket.value.onerror = (error) => {
          logger.error('WebSocket error:', error)
          reject(error)
        }

      } catch (error) {
        logger.error('Error creating WebSocket:', error)
        connectionState.value = ConnectionState.DISCONNECTED
        reject(error)
      }
    })
  }

  /**
   * 安排重新連接
   */
  const scheduleReconnect = () => {
    reconnectAttempts.value++
    logger.log(`Reconnecting... (${reconnectAttempts.value}/${maxReconnectAttempts})`)

    setTimeout(() => {
      if (userStore.isAuthenticated) {
        connect()
      }
    }, reconnectDelay)
  }

  /**
   * 斷開連接
   */
  const disconnect = () => {
    if (socket.value) {
      socket.value.close(1000, 'Client disconnect')
      socket.value = null
    }
    connectionState.value = ConnectionState.DISCONNECTED
    reconnectAttempts.value = maxReconnectAttempts // 防止自動重連
  }

  /**
   * 發送訊息
   */
  const send = (data) => {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) {
      logger.error('WebSocket not connected, readyState:', socket.value?.readyState)
      return false
    }

    try {
      logger.debug('[WebSocket] Sending message:', data.type)
      socket.value.send(JSON.stringify(data))
      return true
    } catch (error) {
      logger.error('Error sending message:', error)
      return false
    }
  }

  /**
   * 發送聊天訊息
   */
  const sendChatMessage = (matchId, content, messageType = 'TEXT') => {
    return send({
      type: 'chat_message',
      match_id: matchId,
      content,
      message_type: messageType
    })
  }

  /**
   * 發送打字指示器
   */
  const sendTypingIndicator = (matchId, isTyping) => {
    logger.debug('[WebSocket] Sending typing indicator:', { matchId, isTyping })
    return send({
      type: 'typing',
      match_id: matchId,
      is_typing: isTyping
    })
  }

  /**
   * 發送已讀回條
   */
  const sendReadReceipt = (messageId) => {
    return send({
      type: 'read_receipt',
      message_id: messageId
    })
  }

  /**
   * 加入配對聊天室
   */
  const joinMatch = (matchId) => {
    logger.debug('[WebSocket] Joining match room:', matchId)
    const result = send({
      type: 'join_match',
      match_id: matchId
    })
    logger.debug('[WebSocket] Join match result:', result)
    return result
  }

  /**
   * 離開配對聊天室
   */
  const leaveMatch = (matchId) => {
    return send({
      type: 'leave_match',
      match_id: matchId
    })
  }

  /**
   * 註冊訊息處理器
   */
  const onMessage = (type, handler) => {
    if (!messageHandlers.value.has(type)) {
      messageHandlers.value.set(type, [])
    }
    messageHandlers.value.get(type).push(handler)

    // 返回取消註冊函數
    return () => {
      const handlers = messageHandlers.value.get(type)
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  /**
   * 發送心跳回應 (pong)
   * 用於回應伺服器的 ping 訊息，維持連接狀態
   */
  const sendPong = () => {
    return send({
      type: 'pong'
    })
  }

  /**
   * 處理收到的訊息
   */
  const handleMessage = (data) => {
    const { type } = data

    // 執行已註冊的處理器
    const handlers = messageHandlers.value.get(type) || []
    handlers.forEach(handler => {
      try {
        handler(data)
      } catch (error) {
        logger.error(`Error in message handler for ${type}:`, error)
      }
    })

    // 預設處理
    switch (type) {
      case 'connection':
        logger.log('Connection status:', data.status)
        break
      case 'ping':
        // 收到伺服器的心跳 ping，立即回應 pong
        sendPong()
        logger.debug('Received ping, sent pong')
        break
      case 'error':
        logger.error('WebSocket error message:', data.message)
        break
      default:
        // 由具體的處理器處理
        break
    }
  }

  /**
   * 清理資源
   */
  onUnmounted(() => {
    disconnect()
    messageHandlers.value.clear()
  })

  return {
    // State
    socket,
    connectionState,
    reconnectAttempts,

    // Getters
    isConnected,
    isConnecting,

    // Methods
    connect,
    disconnect,
    send,
    sendChatMessage,
    sendTypingIndicator,
    sendReadReceipt,
    joinMatch,
    leaveMatch,
    onMessage,

    // Constants
    ConnectionState
  }
}
