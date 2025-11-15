/**
 * Discovery Store 單元測試
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDiscoveryStore } from '@/stores/discovery'
import apiClient from '@/api/client'

// Mock apiClient
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}))

describe('Discovery Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('初始狀態', () => {
    it('應該初始化為空狀態', () => {
      const store = useDiscoveryStore()

      expect(store.candidates).toEqual([])
      expect(store.matches).toEqual([])
      expect(store.currentCandidate).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.lastMatchedUser).toBeNull()
    })
  })

  describe('瀏覽候選人', () => {
    it('應該成功獲取候選人列表', async () => {
      const store = useDiscoveryStore()
      const mockCandidates = [
        { id: 'user1', display_name: 'Alice', age: 25, bio: 'Hello' },
        { id: 'user2', display_name: 'Bob', age: 28, bio: 'Hi' },
        { id: 'user3', display_name: 'Charlie', age: 30, bio: 'Hey' }
      ]

      apiClient.get.mockResolvedValue({ data: mockCandidates })

      const result = await store.browseCandidates(20)

      expect(apiClient.get).toHaveBeenCalledWith('/discovery/browse', {
        params: { limit: 20 }
      })
      expect(store.candidates).toEqual(mockCandidates)
      expect(store.currentCandidate).toEqual(mockCandidates[0])
      expect(result).toEqual(mockCandidates)
      expect(store.loading).toBe(false)
    })

    it('應該處理空候選人列表', async () => {
      const store = useDiscoveryStore()

      apiClient.get.mockResolvedValue({ data: [] })

      await store.browseCandidates()

      expect(store.candidates).toEqual([])
      expect(store.currentCandidate).toBeNull()
    })

    it('應該處理獲取候選人失敗', async () => {
      const store = useDiscoveryStore()

      apiClient.get.mockRejectedValue({
        response: {
          data: {
            detail: '無法取得候選人列表'
          }
        }
      })

      await expect(store.browseCandidates()).rejects.toThrow()
      expect(store.error).toBe('無法取得候選人列表')
    })

    it('應該使用預設限制數量', async () => {
      const store = useDiscoveryStore()

      apiClient.get.mockResolvedValue({ data: [] })

      await store.browseCandidates()

      expect(apiClient.get).toHaveBeenCalledWith('/discovery/browse', {
        params: { limit: 20 }
      })
    })
  })

  describe('喜歡用戶', () => {
    it('應該成功喜歡用戶（未配對）', async () => {
      const store = useDiscoveryStore()

      store.candidates = [
        { id: 'user1', display_name: 'Alice' },
        { id: 'user2', display_name: 'Bob' }
      ]
      store.currentCandidate = store.candidates[0]

      apiClient.post.mockResolvedValue({
        data: { liked: true, matched: false }
      })

      const result = await store.likeUser('user1')

      expect(apiClient.post).toHaveBeenCalledWith('/discovery/like/user1')
      expect(result.liked).toBe(true)
      expect(result.matched).toBe(false)
      expect(store.candidates.length).toBe(1)
      expect(store.currentCandidate.id).toBe('user2')
    })

    it('應該成功喜歡用戶並配對成功', async () => {
      const store = useDiscoveryStore()

      store.candidates = [
        { id: 'user1', display_name: 'Alice' },
        { id: 'user2', display_name: 'Bob' }
      ]
      store.currentCandidate = store.candidates[0]

      apiClient.post.mockResolvedValue({
        data: { liked: true, matched: true, match_id: 'match123' }
      })

      // Mock fetchMatches
      apiClient.get.mockResolvedValue({
        data: [{ match_id: 'match123', user: { id: 'user1', display_name: 'Alice' } }]
      })

      const result = await store.likeUser('user1')

      expect(result.matched).toBe(true)
      expect(result.match_id).toBe('match123')
      expect(store.lastMatchedUser).toEqual({ id: 'user1', display_name: 'Alice' })
      expect(store.matches.length).toBe(1)
    })

    it('應該移除最後一個候選人後設置 currentCandidate 為 null', async () => {
      const store = useDiscoveryStore()

      store.candidates = [{ id: 'user1', display_name: 'Alice' }]
      store.currentCandidate = store.candidates[0]

      apiClient.post.mockResolvedValue({
        data: { liked: true, matched: false }
      })

      await store.likeUser('user1')

      expect(store.candidates).toEqual([])
      expect(store.currentCandidate).toBeNull()
    })

    it('應該處理喜歡用戶失敗', async () => {
      const store = useDiscoveryStore()

      apiClient.post.mockRejectedValue({
        response: {
          data: {
            detail: '操作失敗'
          }
        }
      })

      await expect(store.likeUser('user1')).rejects.toThrow()
      expect(store.error).toBe('操作失敗')
    })
  })

  describe('跳過用戶', () => {
    it('應該成功跳過用戶', async () => {
      const store = useDiscoveryStore()

      store.candidates = [
        { id: 'user1', display_name: 'Alice' },
        { id: 'user2', display_name: 'Bob' }
      ]
      store.currentCandidate = store.candidates[0]

      apiClient.post.mockResolvedValue({ data: { success: true } })

      const result = await store.passUser('user1')

      expect(apiClient.post).toHaveBeenCalledWith('/discovery/pass/user1')
      expect(result).toBe(true)
      expect(store.candidates.length).toBe(1)
      expect(store.currentCandidate.id).toBe('user2')
    })

    it('應該處理跳過用戶失敗', async () => {
      const store = useDiscoveryStore()

      apiClient.post.mockRejectedValue({
        response: {
          data: {
            detail: '操作失敗'
          }
        }
      })

      await expect(store.passUser('user1')).rejects.toThrow()
      expect(store.error).toBe('操作失敗')
    })
  })

  describe('獲取配對列表', () => {
    it('應該成功獲取配對列表', async () => {
      const store = useDiscoveryStore()
      const mockMatches = [
        { match_id: 'match1', user: { id: 'user1', display_name: 'Alice' } },
        { match_id: 'match2', user: { id: 'user2', display_name: 'Bob' } }
      ]

      apiClient.get.mockResolvedValue({ data: mockMatches })

      const result = await store.fetchMatches()

      expect(apiClient.get).toHaveBeenCalledWith('/discovery/matches')
      expect(store.matches).toEqual(mockMatches)
      expect(result).toEqual(mockMatches)
    })

    it('應該處理獲取配對列表失敗', async () => {
      const store = useDiscoveryStore()

      apiClient.get.mockRejectedValue({
        response: {
          data: {
            detail: '無法取得配對列表'
          }
        }
      })

      await expect(store.fetchMatches()).rejects.toThrow()
      expect(store.error).toBe('無法取得配對列表')
    })
  })

  describe('取消配對', () => {
    it('應該成功取消配對', async () => {
      const store = useDiscoveryStore()

      store.matches = [
        { match_id: 'match1', user: { id: 'user1' } },
        { match_id: 'match2', user: { id: 'user2' } }
      ]

      apiClient.delete.mockResolvedValue({ status: 204 })

      const result = await store.unmatch('match1')

      expect(apiClient.delete).toHaveBeenCalledWith('/discovery/unmatch/match1')
      expect(result).toBe(true)
      expect(store.matches.length).toBe(1)
      expect(store.matches[0].match_id).toBe('match2')
    })

    it('應該處理取消配對失敗', async () => {
      const store = useDiscoveryStore()

      apiClient.delete.mockRejectedValue({
        response: {
          data: {
            detail: '取消配對失敗'
          }
        }
      })

      await expect(store.unmatch('match1')).rejects.toThrow()
      expect(store.error).toBe('取消配對失敗')
    })
  })

  describe('移除當前候選人', () => {
    it('應該移除當前候選人並切換到下一個', () => {
      const store = useDiscoveryStore()

      store.candidates = [
        { id: 'user1', display_name: 'Alice' },
        { id: 'user2', display_name: 'Bob' },
        { id: 'user3', display_name: 'Charlie' }
      ]
      store.currentCandidate = store.candidates[0]

      store.removeCurrentCandidate()

      expect(store.candidates.length).toBe(2)
      expect(store.currentCandidate.id).toBe('user2')
    })

    it('應該在移除最後一個候選人時設置 currentCandidate 為 null', () => {
      const store = useDiscoveryStore()

      store.candidates = [{ id: 'user1', display_name: 'Alice' }]
      store.currentCandidate = store.candidates[0]

      store.removeCurrentCandidate()

      expect(store.candidates).toEqual([])
      expect(store.currentCandidate).toBeNull()
    })
  })

  describe('清除上次配對', () => {
    it('應該清除 lastMatchedUser', () => {
      const store = useDiscoveryStore()

      store.lastMatchedUser = { id: 'user1', display_name: 'Alice' }

      store.clearLastMatch()

      expect(store.lastMatchedUser).toBeNull()
    })
  })

  describe('Computed 屬性', () => {
    it('hasCandidates 應該正確判斷是否有候選人', () => {
      const store = useDiscoveryStore()

      expect(store.hasCandidates).toBe(false)

      store.candidates = [{ id: 'user1' }]

      expect(store.hasCandidates).toBe(true)
    })

    it('hasMatches 應該正確判斷是否有配對', () => {
      const store = useDiscoveryStore()

      expect(store.hasMatches).toBe(false)

      store.matches = [{ match_id: 'match1' }]

      expect(store.hasMatches).toBe(true)
    })

    it('matchCount 應該正確計算配對數量', () => {
      const store = useDiscoveryStore()

      expect(store.matchCount).toBe(0)

      store.matches = [
        { match_id: 'match1' },
        { match_id: 'match2' },
        { match_id: 'match3' }
      ]

      expect(store.matchCount).toBe(3)
    })
  })

  describe('錯誤處理', () => {
    it('應該正確清除錯誤訊息', () => {
      const store = useDiscoveryStore()

      store.error = '某個錯誤訊息'

      store.clearError()

      expect(store.error).toBeNull()
    })
  })

  describe('重置 Store', () => {
    it('應該正確重置所有狀態', () => {
      const store = useDiscoveryStore()

      // 設置一些狀態
      store.candidates = [{ id: 'user1' }]
      store.matches = [{ match_id: 'match1' }]
      store.currentCandidate = { id: 'user1' }
      store.lastMatchedUser = { id: 'user2' }
      store.error = 'Some error'

      store.$reset()

      expect(store.candidates).toEqual([])
      expect(store.matches).toEqual([])
      expect(store.currentCandidate).toBeNull()
      expect(store.lastMatchedUser).toBeNull()
      expect(store.error).toBeNull()
      expect(store.loading).toBe(false)
    })
  })
})
