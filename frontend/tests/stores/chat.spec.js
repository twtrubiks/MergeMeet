/**
 * Chat Store 單元測試
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import apiClient from '@/api/client'

// Mock apiClient
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}))

// Mock useWebSocket
const mockWebSocket = {
  connect: vi.fn(),
  disconnect: vi.fn(),
  sendChatMessage: vi.fn(),
  sendTypingIndicator: vi.fn(),
  sendReadReceipt: vi.fn(),
  joinMatch: vi.fn(),
  leaveMatch: vi.fn(),
  onMessage: vi.fn()
}

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => mockWebSocket
}))

describe('Chat Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())

    // 設置已登入用戶
    const userStore = useUserStore()
    userStore.user = { id: 'user123', email: 'test@example.com' }
    userStore.accessToken = 'test_token'

    // 清除所有 mock
    vi.clearAllMocks()
  })

  describe('初始狀態', () => {
    it('應該初始化為空狀態', () => {
      const store = useChatStore()

      expect(store.conversations).toEqual([])
      expect(store.messages).toEqual({})
      expect(store.currentMatchId).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.typingUsers).toEqual({})
    })
  })

  describe('WebSocket 初始化', () => {
    it('應該正確初始化 WebSocket', () => {
      const store = useChatStore()

      store.initWebSocket()

      expect(mockWebSocket.connect).toHaveBeenCalled()
      expect(mockWebSocket.onMessage).toHaveBeenCalledWith('new_message', expect.any(Function))
      expect(mockWebSocket.onMessage).toHaveBeenCalledWith('typing', expect.any(Function))
      expect(mockWebSocket.onMessage).toHaveBeenCalledWith('read_receipt', expect.any(Function))
      expect(mockWebSocket.onMessage).toHaveBeenCalledWith('message_deleted', expect.any(Function))
    })

    it('應該正確關閉 WebSocket', () => {
      const store = useChatStore()

      store.closeWebSocket()

      expect(mockWebSocket.disconnect).toHaveBeenCalled()
    })
  })

  describe('獲取對話列表', () => {
    it('應該成功獲取對話列表', async () => {
      const store = useChatStore()
      const mockConversations = [
        {
          match_id: 'match1',
          other_user: { id: 'user2', display_name: 'Alice' },
          last_message: { content: 'Hello!', sent_at: '2025-11-15T10:00:00Z' },
          unread_count: 2
        },
        {
          match_id: 'match2',
          other_user: { id: 'user3', display_name: 'Bob' },
          last_message: { content: 'Hi!', sent_at: '2025-11-15T09:00:00Z' },
          unread_count: 0
        }
      ]

      apiClient.get.mockResolvedValue({ data: mockConversations })

      const result = await store.fetchConversations()

      expect(apiClient.get).toHaveBeenCalledWith('/messages/conversations')
      expect(store.conversations).toEqual(mockConversations)
      expect(result).toEqual(mockConversations)
      expect(store.loading).toBe(false)
    })

    it('應該處理獲取對話列表失敗', async () => {
      const store = useChatStore()

      apiClient.get.mockRejectedValue({
        response: {
          data: {
            detail: '無法取得對話列表'
          }
        }
      })

      await expect(store.fetchConversations()).rejects.toThrow()
      expect(store.error).toBe('無法取得對話列表')
    })
  })

  describe('獲取聊天記錄', () => {
    it('應該成功獲取聊天記錄', async () => {
      const store = useChatStore()
      const matchId = 'match123'
      const mockMessages = [
        {
          id: 'msg1',
          match_id: matchId,
          sender_id: 'user123',
          content: 'Hello',
          sent_at: '2025-11-15T10:00:00Z'
        },
        {
          id: 'msg2',
          match_id: matchId,
          sender_id: 'user456',
          content: 'Hi!',
          sent_at: '2025-11-15T10:01:00Z'
        }
      ]

      apiClient.get.mockResolvedValue({
        data: {
          messages: mockMessages,
          total: 2,
          page: 1
        }
      })

      await store.fetchChatHistory(matchId)

      expect(apiClient.get).toHaveBeenCalledWith(`/messages/matches/${matchId}/messages`, {
        params: { page: 1, page_size: 50 }
      })
      expect(store.messages[matchId]).toEqual(mockMessages)
    })

    it('應該合併訊息並避免重複', async () => {
      const store = useChatStore()
      const matchId = 'match123'

      // 第一次載入
      const firstBatch = [
        { id: 'msg1', match_id: matchId, content: 'Message 1', sent_at: '2025-11-15T10:00:00Z' }
      ]

      apiClient.get.mockResolvedValue({
        data: { messages: firstBatch }
      })

      await store.fetchChatHistory(matchId, 1)

      // 第二次載入（包含重複訊息）
      const secondBatch = [
        { id: 'msg1', match_id: matchId, content: 'Message 1', sent_at: '2025-11-15T10:00:00Z' },
        { id: 'msg2', match_id: matchId, content: 'Message 2', sent_at: '2025-11-15T10:01:00Z' }
      ]

      apiClient.get.mockResolvedValue({
        data: { messages: secondBatch }
      })

      await store.fetchChatHistory(matchId, 2)

      // 應該只有 2 則不重複的訊息
      expect(store.messages[matchId].length).toBe(2)
      expect(store.messages[matchId].map(m => m.id)).toEqual(['msg1', 'msg2'])
    })

    it('應該按時間排序訊息', async () => {
      const store = useChatStore()
      const matchId = 'match123'

      const unsortedMessages = [
        { id: 'msg3', match_id: matchId, content: 'Third', sent_at: '2025-11-15T10:02:00Z' },
        { id: 'msg1', match_id: matchId, content: 'First', sent_at: '2025-11-15T10:00:00Z' },
        { id: 'msg2', match_id: matchId, content: 'Second', sent_at: '2025-11-15T10:01:00Z' }
      ]

      apiClient.get.mockResolvedValue({
        data: { messages: unsortedMessages }
      })

      await store.fetchChatHistory(matchId)

      expect(store.messages[matchId][0].id).toBe('msg1')
      expect(store.messages[matchId][1].id).toBe('msg2')
      expect(store.messages[matchId][2].id).toBe('msg3')
    })
  })

  describe('發送訊息', () => {
    it('應該透過 WebSocket 發送訊息', async () => {
      const store = useChatStore()
      mockWebSocket.sendChatMessage.mockReturnValue(true)

      await store.sendMessage('match123', 'Hello World!', 'TEXT')

      expect(mockWebSocket.sendChatMessage).toHaveBeenCalledWith('match123', 'Hello World!', 'TEXT')
    })

    it('應該處理空訊息', async () => {
      const store = useChatStore()

      await store.sendMessage('match123', '   ', 'TEXT')

      expect(mockWebSocket.sendChatMessage).not.toHaveBeenCalled()
    })

    it('應該處理 WebSocket 未連接的情況', async () => {
      const store = useChatStore()
      mockWebSocket.sendChatMessage.mockReturnValue(false)

      await expect(store.sendMessage('match123', 'Hello')).rejects.toThrow('WebSocket 未連接')
    })
  })

  describe('刪除訊息', () => {
    it('應該成功刪除訊息', async () => {
      const store = useChatStore()
      const matchId = 'match123'
      const messageId = 'msg123'

      // 設置初始訊息
      store.messages[matchId] = [
        { id: 'msg123', content: 'To be deleted' },
        { id: 'msg456', content: 'Keep this' }
      ]

      apiClient.delete.mockResolvedValue({ status: 204 })

      await store.deleteMessage(messageId)

      expect(apiClient.delete).toHaveBeenCalledWith(`/messages/messages/${messageId}`)
      expect(store.messages[matchId].length).toBe(1)
      expect(store.messages[matchId][0].id).toBe('msg456')
    })

    it('應該處理刪除失敗', async () => {
      const store = useChatStore()

      apiClient.delete.mockRejectedValue({
        response: {
          data: {
            detail: '刪除訊息失敗'
          }
        }
      })

      await expect(store.deleteMessage('msg123')).rejects.toThrow()
      expect(store.error).toBe('刪除訊息失敗')
    })
  })

  describe('標記已讀', () => {
    it('應該標記多則訊息為已讀', async () => {
      const store = useChatStore()
      const messageIds = ['msg1', 'msg2', 'msg3']

      apiClient.post.mockResolvedValue({ data: { success: true } })

      await store.markAsRead(messageIds)

      expect(apiClient.post).toHaveBeenCalledWith('/messages/messages/read', {
        message_ids: messageIds
      })
      expect(mockWebSocket.sendReadReceipt).toHaveBeenCalledTimes(3)
    })

    it('應該處理空訊息列表', async () => {
      const store = useChatStore()

      await store.markAsRead([])

      expect(apiClient.post).not.toHaveBeenCalled()
    })

    it('應該標記對話中所有未讀訊息為已讀', async () => {
      const store = useChatStore()
      const matchId = 'match123'

      store.messages[matchId] = [
        { id: 'msg1', sender_id: 'user456', is_read: false },
        { id: 'msg2', sender_id: 'user123', is_read: false }, // 自己的訊息
        { id: 'msg3', sender_id: 'user456', is_read: false },
        { id: 'msg4', sender_id: 'user456', is_read: true }  // 已讀
      ]

      store.conversations = [
        { match_id: matchId, unread_count: 2 }
      ]

      apiClient.post.mockResolvedValue({ data: { success: true } })

      await store.markConversationAsRead(matchId)

      expect(apiClient.post).toHaveBeenCalledWith('/messages/messages/read', {
        message_ids: ['msg1', 'msg3']
      })

      expect(store.conversations[0].unread_count).toBe(0)
    })
  })

  describe('打字指示器', () => {
    it('應該發送打字指示器', () => {
      const store = useChatStore()

      store.sendTyping('match123', true)

      expect(mockWebSocket.sendTypingIndicator).toHaveBeenCalledWith('match123', true)
    })
  })

  describe('加入/離開聊天室', () => {
    it('應該加入配對聊天室', async () => {
      const store = useChatStore()
      const matchId = 'match123'

      apiClient.get.mockResolvedValue({
        data: { messages: [] }
      })

      await store.joinMatchRoom(matchId)

      expect(store.currentMatchId).toBe(matchId)
      expect(mockWebSocket.joinMatch).toHaveBeenCalledWith(matchId)
    })

    it('應該離開配對聊天室', () => {
      const store = useChatStore()
      store.currentMatchId = 'match123'

      store.leaveMatchRoom()

      expect(mockWebSocket.leaveMatch).toHaveBeenCalledWith('match123')
      expect(store.currentMatchId).toBeNull()
    })
  })

  // 注意：handleNewMessage, handleTypingIndicator, handleReadReceipt, handleMessageDeleted
  // 是內部函數，不直接測試。它們的邏輯會在集成測試或端到端測試中被覆蓋。
  // 我們已經在 "WebSocket 初始化" 測試中驗證了這些處理器被正確註冊。

  describe('Computed 屬性', () => {
    it('currentConversation 應該返回當前對話', () => {
      const store = useChatStore()

      store.conversations = [
        { match_id: 'match1', other_user: { display_name: 'Alice' } },
        { match_id: 'match2', other_user: { display_name: 'Bob' } }
      ]

      store.currentMatchId = 'match2'

      expect(store.currentConversation.other_user.display_name).toBe('Bob')
    })

    it('currentMessages 應該返回當前對話的訊息', () => {
      const store = useChatStore()

      store.messages = {
        match1: [{ id: 'msg1' }],
        match2: [{ id: 'msg2' }, { id: 'msg3' }]
      }

      store.currentMatchId = 'match2'

      expect(store.currentMessages.length).toBe(2)
      expect(store.currentMessages[0].id).toBe('msg2')
    })

    it('unreadCount 應該計算總未讀數', () => {
      const store = useChatStore()

      store.conversations = [
        { match_id: 'match1', unread_count: 3 },
        { match_id: 'match2', unread_count: 5 },
        { match_id: 'match3', unread_count: 0 }
      ]

      expect(store.unreadCount).toBe(8)
    })

    it('isTyping 應該正確判斷當前對話是否有人在打字', () => {
      const store = useChatStore()

      store.currentMatchId = 'match123'
      store.typingUsers = {}

      expect(store.isTyping).toBe(false)

      store.typingUsers = { match123: 'user456' }

      expect(store.isTyping).toBe(true)
    })
  })

  describe('重置 Store', () => {
    it('應該正確重置所有狀態', () => {
      const store = useChatStore()

      // 設置一些狀態
      store.conversations = [{ match_id: 'match1' }]
      store.messages = { match1: [{ id: 'msg1' }] }
      store.currentMatchId = 'match1'
      store.error = 'Some error'

      store.$reset()

      expect(store.conversations).toEqual([])
      expect(store.messages).toEqual({})
      expect(store.currentMatchId).toBeNull()
      expect(store.error).toBeNull()
      expect(mockWebSocket.disconnect).toHaveBeenCalled()
    })
  })
})
