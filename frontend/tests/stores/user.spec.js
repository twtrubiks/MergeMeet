/**
 * User Store 單元測試
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import { authAPI } from '@/api/auth'

// Mock authAPI
vi.mock('@/api/auth', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
    refreshToken: vi.fn()
  }
}))

describe('User Store', () => {
  beforeEach(() => {
    // 每次測試前創建新的 Pinia 實例
    setActivePinia(createPinia())

    // 清除 localStorage 並設置預設返回值為 null
    localStorage.clear()
    localStorage.getItem.mockReturnValue(null)
    localStorage.getItem.mockClear()
    localStorage.setItem.mockClear()
    localStorage.removeItem.mockClear()

    // 清除所有 mock
    vi.clearAllMocks()
  })

  describe('初始狀態', () => {
    it('應該初始化為未登入狀態', () => {
      const store = useUserStore()

      expect(store.user).toBeNull()
      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('應該從 localStorage 載入 token', () => {
      localStorage.getItem.mockImplementation((key) => {
        if (key === 'access_token') return 'stored_access_token'
        if (key === 'refresh_token') return 'stored_refresh_token'
        return null
      })

      const store = useUserStore()

      expect(store.accessToken).toBe('stored_access_token')
      expect(store.refreshToken).toBe('stored_refresh_token')
    })
  })

  describe('註冊功能', () => {
    it('應該成功註冊用戶', async () => {
      const store = useUserStore()
      const mockResponse = {
        access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlfQ.test',
        refresh_token: 'mock_refresh_token'
      }

      authAPI.register.mockResolvedValue(mockResponse)

      const result = await store.register({
        email: 'test@example.com',
        password: 'Password123',
        date_of_birth: '1995-01-01'
      })

      expect(result).toBe(true)
      expect(store.accessToken).toBe(mockResponse.access_token)
      expect(store.refreshToken).toBe(mockResponse.refresh_token)
      expect(store.isAuthenticated).toBe(true)
      expect(store.user).toBeTruthy()
      expect(store.user.id).toBe('user123')
      expect(store.user.email).toBe('test@example.com')
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', mockResponse.access_token)
      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', mockResponse.refresh_token)
    })

    it('應該處理註冊失敗（電子郵件已被使用）', async () => {
      const store = useUserStore()
      const mockError = {
        response: {
          data: {
            detail: '電子郵件已被使用'
          }
        }
      }

      authAPI.register.mockRejectedValue(mockError)

      const result = await store.register({
        email: 'test@example.com',
        password: 'Password123',
        date_of_birth: '1995-01-01'
      })

      expect(result).toBe(false)
      expect(store.error).toBe('電子郵件已被使用')
      expect(store.isAuthenticated).toBe(false)
      expect(store.user).toBeNull()
    })

    it('應該處理註冊失敗（無詳細訊息）', async () => {
      const store = useUserStore()
      authAPI.register.mockRejectedValue(new Error('Network error'))

      const result = await store.register({
        email: 'test@example.com',
        password: 'Password123'
      })

      expect(result).toBe(false)
      expect(store.error).toBe('註冊失敗')
    })
  })

  describe('登入功能', () => {
    it('應該成功登入用戶', async () => {
      const store = useUserStore()
      const mockResponse = {
        access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIn0.test',
        refresh_token: 'mock_refresh_token'
      }

      authAPI.login.mockResolvedValue(mockResponse)

      const result = await store.login({
        email: 'test@example.com',
        password: 'Password123'
      })

      expect(result).toBe(true)
      expect(store.isAuthenticated).toBe(true)
      expect(store.user).toBeTruthy()
      expect(authAPI.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'Password123'
      })
    })

    it('應該處理登入失敗（密碼錯誤）', async () => {
      const store = useUserStore()
      const mockError = {
        response: {
          data: {
            detail: '電子郵件或密碼錯誤'
          }
        }
      }

      authAPI.login.mockRejectedValue(mockError)

      const result = await store.login({
        email: 'test@example.com',
        password: 'WrongPassword'
      })

      expect(result).toBe(false)
      expect(store.error).toBe('電子郵件或密碼錯誤')
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('登出功能', () => {
    it('應該正確登出並清除狀態', () => {
      const store = useUserStore()

      // 設置已登入狀態
      store.accessToken = 'test_token'
      store.refreshToken = 'test_refresh'
      store.user = { id: '123', email: 'test@example.com' }

      store.logout()

      expect(store.user).toBeNull()
      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
    })
  })

  describe('Email 驗證', () => {
    it('應該成功驗證 Email', async () => {
      const store = useUserStore()
      store.user = { id: '123', email: 'test@example.com', email_verified: false }

      authAPI.verifyEmail.mockResolvedValue({ success: true })

      const result = await store.verifyEmail('123456')

      expect(result).toBe(true)
      expect(store.user.email_verified).toBe(true)
      expect(authAPI.verifyEmail).toHaveBeenCalledWith({
        email: 'test@example.com',
        verification_code: '123456'
      })
    })

    it('應該處理驗證失敗（無用戶 Email）', async () => {
      const store = useUserStore()
      store.user = null

      const result = await store.verifyEmail('123456')

      expect(result).toBe(false)
      expect(store.error).toBe('找不到用戶 Email')
    })

    it('應該處理驗證失敗（驗證碼錯誤）', async () => {
      const store = useUserStore()
      store.user = { id: '123', email: 'test@example.com' }

      authAPI.verifyEmail.mockRejectedValue({
        response: {
          data: {
            detail: '驗證碼錯誤'
          }
        }
      })

      const result = await store.verifyEmail('000000')

      expect(result).toBe(false)
      expect(store.error).toBe('驗證碼錯誤')
    })
  })

  describe('重新發送驗證碼', () => {
    it('應該成功重新發送驗證碼', async () => {
      const store = useUserStore()
      store.user = { id: '123', email: 'test@example.com' }

      authAPI.resendVerification.mockResolvedValue({ success: true })

      const result = await store.resendVerification()

      expect(result).toBe(true)
      expect(authAPI.resendVerification).toHaveBeenCalledWith('test@example.com')
    })

    it('應該處理無用戶 Email 的情況', async () => {
      const store = useUserStore()
      store.user = null

      const result = await store.resendVerification()

      expect(result).toBe(false)
      expect(store.error).toBe('找不到用戶 Email')
    })
  })

  describe('Token 管理', () => {
    it('應該正確儲存 Tokens', () => {
      const store = useUserStore()

      store.saveTokens({
        access_token: 'new_access_token',
        refresh_token: 'new_refresh_token'
      })

      expect(store.accessToken).toBe('new_access_token')
      expect(store.refreshToken).toBe('new_refresh_token')
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'new_access_token')
      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'new_refresh_token')
    })

    it('應該正確清除 Tokens', () => {
      const store = useUserStore()
      store.accessToken = 'test_token'
      store.user = { id: '123' }

      store.clearTokens()

      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.user).toBeNull()
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
    })

    it('應該從 JWT Token 正確解析用戶資料', () => {
      const store = useUserStore()

      // 有效的 JWT token (payload: {sub: "user123", email: "test@example.com", email_verified: true})
      const validToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWV9.test'

      store.accessToken = validToken
      store.initializeFromToken()

      expect(store.user).toBeTruthy()
      expect(store.user.id).toBe('user123')
      expect(store.user.email).toBe('test@example.com')
      expect(store.user.email_verified).toBe(true)
    })

    it('應該處理無效的 JWT Token', () => {
      const store = useUserStore()
      store.accessToken = 'invalid_token'

      store.initializeFromToken()

      expect(store.user).toBeNull()
      expect(store.accessToken).toBeNull()
    })
  })

  describe('Computed 屬性', () => {
    it('isAuthenticated 應該根據 accessToken 正確計算', () => {
      const store = useUserStore()

      expect(store.isAuthenticated).toBe(false)

      store.accessToken = 'test_token'
      expect(store.isAuthenticated).toBe(true)

      store.accessToken = null
      expect(store.isAuthenticated).toBe(false)
    })

    it('userEmail 應該正確返回用戶 Email', () => {
      const store = useUserStore()

      expect(store.userEmail).toBeNull()

      store.user = { id: '123', email: 'test@example.com' }
      expect(store.userEmail).toBe('test@example.com')
    })
  })

  describe('錯誤處理', () => {
    it('應該正確清除錯誤訊息', () => {
      const store = useUserStore()
      store.error = '某個錯誤訊息'

      store.clearError()

      expect(store.error).toBeNull()
    })
  })
})
