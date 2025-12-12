/**
 * 全域 WebSocket Store
 *
 * 管理全域 WebSocket 連接，在用戶認證狀態變化時自動連接/斷開
 * 提供統一的訊息處理器註冊機制
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useUserStore } from './user'
import { logger } from '@/utils/logger'

// WebSocket 連接狀態
export const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting'
}

export const useWebSocketStore = defineStore('websocket', () => {
  // State
  const socket = ref(null)
  const connectionState = ref(ConnectionState.DISCONNECTED)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 10  // 增加重試次數
  const baseReconnectDelay = 1000

  // 使用普通 Map（不用 ref 包裹，避免序列化問題）
  // 這個 Map 不需要響應式，因為它只在內部使用
  const messageHandlers = new Map()

  // 儲存正在進行的連接 Promise（避免重複連接）
  let connectingPromise = null
  let reconnectTimer = null

  // Getters
  const isConnected = computed(() => connectionState.value === ConnectionState.CONNECTED)
  const isConnecting = computed(() =>
    connectionState.value === ConnectionState.CONNECTING ||
    connectionState.value === ConnectionState.RECONNECTING
  )

  /**
   * 指數退避重連延遲
   * @returns {number} 延遲毫秒數
   */
  const getReconnectDelay = () => {
    return Math.min(baseReconnectDelay * Math.pow(2, reconnectAttempts.value), 30000)
  }

  /**
   * 建立 WebSocket 連接（使用首次訊息認證）
   * @returns {Promise<void>}
   */
  const connect = () => {
    const userStore = useUserStore()

    // 已連接，直接返回
    if (socket.value?.readyState === WebSocket.OPEN) {
      logger.log('[GlobalWS] Already connected')
      return Promise.resolve()
    }

    // 正在連接中，返回現有的 Promise
    if (connectingPromise && (connectionState.value === ConnectionState.CONNECTING ||
        connectionState.value === ConnectionState.RECONNECTING)) {
      logger.log('[GlobalWS] Connection in progress, waiting...')
      return connectingPromise
    }

    if (!userStore.isAuthenticated || !userStore.user?.id) {
      logger.error('[GlobalWS] Cannot connect: User not authenticated')
      return Promise.reject(new Error('User not authenticated'))
    }

    connectionState.value = reconnectAttempts.value > 0
      ? ConnectionState.RECONNECTING
      : ConnectionState.CONNECTING

    connectingPromise = new Promise((resolve, reject) => {
      try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsHost = import.meta.env.VITE_WS_URL || 'localhost:8000'
        const token = userStore.accessToken
        const userId = userStore.user.id

        const wsUrl = `${wsProtocol}//${wsHost}/ws`
        logger.log(`[GlobalWS] Connecting to ${wsUrl}...`)

        socket.value = new WebSocket(wsUrl)

        // 連接成功後立即發送認證訊息
        socket.value.onopen = () => {
          logger.log('[GlobalWS] Connected, sending auth...')

          if (!socket.value) {
            logger.error('[GlobalWS] Socket closed before auth')
            connectingPromise = null
            reject(new Error('WebSocket closed unexpectedly'))
            return
          }

          // 發送認證訊息
          socket.value.send(JSON.stringify({
            type: 'auth',
            token: token,
            user_id: userId
          }))

          // 等待認證成功回應
          const authTimeout = setTimeout(() => {
            logger.error('[GlobalWS] Authentication timeout')
            connectingPromise = null
            socket.value?.close()
            reject(new Error('Authentication timeout'))
          }, 5000)

          // 暫存 onmessage 處理器以接收認證回應
          const tempMessageHandler = (event) => {
            try {
              const data = JSON.parse(event.data)

              if (data.type === 'auth_success') {
                clearTimeout(authTimeout)
                logger.log('[GlobalWS] Authenticated successfully')
                connectionState.value = ConnectionState.CONNECTED
                reconnectAttempts.value = 0
                connectingPromise = null

                // 移除臨時處理器，啟用正常訊息處理
                socket.value.onmessage = normalMessageHandler
                resolve()
              } else if (data.type === 'error' && data.message?.includes('auth')) {
                clearTimeout(authTimeout)
                logger.error('[GlobalWS] Authentication failed:', data.message)
                connectingPromise = null
                socket.value?.close()
                reject(new Error('Authentication failed'))
              }
            } catch (error) {
              logger.error('[GlobalWS] Error parsing auth response:', error)
            }
          }

          socket.value.onmessage = tempMessageHandler
        }

        // 正常訊息處理器
        const normalMessageHandler = (event) => {
          try {
            const data = JSON.parse(event.data)
            handleMessage(data)
          } catch (error) {
            logger.error('[GlobalWS] Error parsing message:', error)
          }
        }

        // 連接關閉
        socket.value.onclose = (event) => {
          logger.log('[GlobalWS] Closed:', event.code, event.reason)
          connectionState.value = ConnectionState.DISCONNECTED
          socket.value = null
          connectingPromise = null

          // 嘗試重新連接（除非是正常關閉或達到上限）
          if (event.code !== 1000 && reconnectAttempts.value < maxReconnectAttempts) {
            scheduleReconnect()
          }
        }

        // 連接錯誤
        socket.value.onerror = (error) => {
          logger.error('[GlobalWS] Error:', error)
          connectingPromise = null
          reject(error)
        }

      } catch (error) {
        logger.error('[GlobalWS] Error creating WebSocket:', error)
        connectionState.value = ConnectionState.DISCONNECTED
        connectingPromise = null
        reject(error)
      }
    })

    return connectingPromise
  }

  /**
   * 安排重新連接（指數退避）
   */
  const scheduleReconnect = () => {
    const userStore = useUserStore()

    // 清除之前的重連計時器
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }

    reconnectAttempts.value++
    const delay = getReconnectDelay()
    logger.log(`[GlobalWS] Reconnecting in ${delay}ms... (${reconnectAttempts.value}/${maxReconnectAttempts})`)

    reconnectTimer = setTimeout(() => {
      if (userStore.isAuthenticated) {
        connect()
      }
    }, delay)
  }

  /**
   * 斷開連接
   */
  const disconnect = () => {
    logger.log('[GlobalWS] Disconnecting...')

    // 清除重連計時器
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    connectingPromise = null

    if (socket.value) {
      socket.value.close(1000, 'Client disconnect')
      socket.value = null
    }

    connectionState.value = ConnectionState.DISCONNECTED
    reconnectAttempts.value = maxReconnectAttempts // 防止自動重連
  }

  /**
   * 發送訊息
   * @param {object} data - 要發送的資料
   * @returns {boolean} 是否發送成功
   */
  const send = (data) => {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) {
      logger.error('[GlobalWS] Not connected, readyState:', socket.value?.readyState)
      return false
    }

    try {
      logger.debug('[GlobalWS] Sending:', data.type)
      socket.value.send(JSON.stringify(data))
      return true
    } catch (error) {
      logger.error('[GlobalWS] Error sending:', error)
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
    logger.debug('[GlobalWS] Joining match:', matchId)
    return send({
      type: 'join_match',
      match_id: matchId
    })
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
   * @param {string} type - 訊息類型
   * @param {function} handler - 處理函數
   * @returns {function} 取消註冊函數
   */
  const onMessage = (type, handler) => {
    if (!messageHandlers.has(type)) {
      messageHandlers.set(type, [])
    }
    messageHandlers.get(type).push(handler)

    // 返回取消註冊函數
    return () => {
      const handlers = messageHandlers.get(type)
      if (handlers) {
        const index = handlers.indexOf(handler)
        if (index > -1) {
          handlers.splice(index, 1)
        }
      }
    }
  }

  /**
   * 發送心跳回應 (pong)
   */
  const sendPong = () => {
    return send({ type: 'pong' })
  }

  /**
   * 處理收到的訊息
   * @param {object} data - 訊息資料
   */
  const handleMessage = (data) => {
    const { type } = data

    // 執行已註冊的處理器
    const handlers = messageHandlers.get(type) || []
    handlers.forEach(handler => {
      try {
        handler(data)
      } catch (error) {
        logger.error(`[GlobalWS] Handler error for ${type}:`, error)
      }
    })

    // 預設處理
    switch (type) {
      case 'ping':
        sendPong()
        logger.debug('[GlobalWS] Received ping, sent pong')
        break
      case 'error':
        logger.error('[GlobalWS] Server error:', data.message)
        break
      default:
        // 由具體的處理器處理
        break
    }
  }

  /**
   * 初始化：監聽用戶認證狀態自動連接/斷開
   */
  const initAutoConnect = () => {
    const userStore = useUserStore()

    watch(
      () => userStore.isAuthenticated,
      (isAuth) => {
        if (isAuth) {
          logger.log('[GlobalWS] User authenticated, connecting...')
          connect().catch(err => {
            logger.error('[GlobalWS] Auto-connect failed:', err)
          })
        } else {
          logger.log('[GlobalWS] User logged out, disconnecting...')
          disconnect()
        }
      },
      { immediate: true }
    )
  }

  /**
   * 重置 Store
   */
  const $reset = () => {
    disconnect()
    messageHandlers.clear()
    reconnectAttempts.value = 0
  }

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
    initAutoConnect,
    $reset,

    // Constants
    ConnectionState
  }
})
