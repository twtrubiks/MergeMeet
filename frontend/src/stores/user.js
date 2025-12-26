/**
 * 用戶狀態管理 (Pinia Store)
 *
 * Token 存儲安全策略（雙模式支援）：
 * 1. HttpOnly Cookie（優先）- 後端自動設置，防止 XSS 攻擊
 * 2. localStorage（回退）- 向後兼容，支援開發過渡期
 *
 * 認證流程：
 * - 登入/註冊：後端設置 HttpOnly Cookie，同時返回 Token 給前端存儲
 * - 請求：前端自動帶 Cookie + CSRF Token，或回退到 Bearer Token
 * - 登出：呼叫後端 API 使 Token 失效 + 清除 Cookie + 清除 localStorage
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '@/api/auth'
import { logger } from '@/utils/logger'

export const useUserStore = defineStore('user', () => {
  // 狀態
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)
  const isLoading = ref(false)
  const error = ref(null)

  // 登入限制狀態
  const loginLimitInfo = ref({
    remainingAttempts: null,
    lockoutSeconds: 0,
    isLocked: false
  })

  // 計算屬性
  const isAuthenticated = computed(() => !!accessToken.value)
  const userEmail = computed(() => user.value?.email || null)
  const isAdmin = computed(() => user.value?.is_admin === true)

  /**
   * 儲存 Token 到 localStorage 和狀態
   */
  const saveTokens = (tokens) => {
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token

    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
  }

  /**
   * 清除 Token
   */
  const clearTokens = () => {
    accessToken.value = null
    refreshToken.value = null
    user.value = null

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  /**
   * 用戶註冊
   * @param {Object} registerData - 註冊資料
   * @returns {Promise<boolean>} 是否成功
   */
  const register = async (registerData) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await authAPI.register(registerData)
      saveTokens(response)

      // 從 Token 初始化用戶資訊（包含 user.id）
      initializeFromToken()

      return true
    } catch (err) {
      error.value = err.response?.data?.detail || '註冊失敗'
      logger.error('註冊錯誤:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 用戶登入
   * @param {Object} credentials - 登入憑證
   * @returns {Promise<boolean>} 是否成功
   */
  const login = async (credentials) => {
    isLoading.value = true
    error.value = null
    // 重置登入限制狀態
    loginLimitInfo.value = { remainingAttempts: null, lockoutSeconds: 0, isLocked: false }

    try {
      const result = await authAPI.login(credentials)

      if (result.success) {
        saveTokens(result.data)
        // 從 Token 初始化用戶資訊（包含 user.id）
        initializeFromToken()
        return true
      } else {
        // 登入失敗，更新限制狀態
        error.value = result.error
        loginLimitInfo.value = {
          remainingAttempts: result.remainingAttempts,
          lockoutSeconds: result.lockoutSeconds,
          isLocked: result.isLocked
        }
        return false
      }
    } catch (err) {
      error.value = '登入失敗'
      logger.error('登入錯誤:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 重置登入限制狀態
   */
  const resetLoginLimitInfo = () => {
    loginLimitInfo.value = {
      remainingAttempts: null,
      lockoutSeconds: 0,
      isLocked: false
    }
  }

  /**
   * 用戶登出
   *
   * 完整登出流程：
   * 1. 呼叫後端 API 使 Token 失效（加入黑名單）
   * 2. 後端清除 HttpOnly Cookie
   * 3. 前端清除 localStorage（向後兼容）
   *
   * @returns {Promise<boolean>} 是否成功
   */
  const logout = async () => {
    try {
      // 呼叫後端登出 API（會清除 Cookie 並使 Token 失效）
      await authAPI.logout()
      logger.info('登出成功，Token 已失效')
    } catch (err) {
      // 即使 API 失敗也要清除本地狀態（例如網路錯誤）
      logger.warn('登出 API 失敗，仍清除本地狀態:', err.message)
    } finally {
      // 無論如何都清除本地狀態
      clearTokens()
    }
  }

  /**
   * 驗證 Email
   * @param {string} verificationCode - 驗證碼
   * @returns {Promise<boolean>} 是否成功
   */
  const verifyEmail = async (verificationCode) => {
    if (!user.value?.email) {
      error.value = '找不到用戶 Email'
      return false
    }

    isLoading.value = true
    error.value = null

    try {
      await authAPI.verifyEmail({
        email: user.value.email,
        verification_code: verificationCode,
      })

      // 更新用戶狀態
      if (user.value) {
        user.value.email_verified = true
      }

      return true
    } catch (err) {
      error.value = err.response?.data?.detail || '驗證失敗'
      logger.error('驗證錯誤:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 重新發送驗證碼
   * @returns {Promise<boolean>} 是否成功
   */
  const resendVerification = async () => {
    if (!user.value?.email) {
      error.value = '找不到用戶 Email'
      return false
    }

    isLoading.value = true
    error.value = null

    try {
      await authAPI.resendVerification(user.value.email)
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || '重新發送失敗'
      logger.error('重新發送錯誤:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 清除錯誤訊息
   */
  const clearError = () => {
    error.value = null
  }

  /**
   * Base64URL 解碼（JWT 使用 base64url 編碼，非標準 base64）
   *
   * JWT 的 base64url 編碼：
   * - 使用 '-' 代替 '+'
   * - 使用 '_' 代替 '/'
   * - 不使用 padding '='
   *
   * @param {string} str - Base64URL 編碼的字串
   * @returns {string} 解碼後的字串
   */
  const base64UrlDecode = (str) => {
    // 將 base64url 轉換為標準 base64
    let base64 = str.replace(/-/g, '+').replace(/_/g, '/')

    // 補齊 padding
    const pad = base64.length % 4
    if (pad) {
      base64 += '='.repeat(4 - pad)
    }

    return atob(base64)
  }

  /**
   * 從 JWT Token 解析用戶資料並初始化
   * is_admin 直接從 token 解析，更安全（無法被用戶偽造）
   */
  const initializeFromToken = () => {
    if (!accessToken.value) {
      return
    }

    try {
      // 解析 JWT token (格式: header.payload.signature)
      const payload = accessToken.value.split('.')[1]
      const decodedPayload = JSON.parse(base64UrlDecode(payload))

      // 從 token 提取用戶資訊（包含 is_admin）
      if (decodedPayload.sub) {
        user.value = {
          id: decodedPayload.sub,
          email: decodedPayload.email || null,
          email_verified: decodedPayload.email_verified || false,
          is_admin: decodedPayload.is_admin || false
        }
      }
    } catch (err) {
      logger.error('Failed to decode token:', err)
      // Token 無效，清除
      clearTokens()
    }
  }

  /**
   * 監聽 Token 刷新事件
   *
   * 當 client.js 自動刷新 Token 成功後，會觸發 'token-refreshed' 事件，
   * 這裡監聽並更新 Pinia Store 狀態，確保前端狀態與實際 Token 同步。
   *
   * 解決問題：Token 刷新後 Pinia Store 不同步
   */
  if (typeof window !== 'undefined') {
    window.addEventListener('token-refreshed', (event) => {
      const { access_token, refresh_token } = event.detail
      if (access_token && refresh_token) {
        saveTokens({ access_token, refresh_token })
        initializeFromToken()
        logger.debug('Token refreshed, store updated')
      }
    })
  }

  return {
    // 狀態
    user,
    accessToken,
    refreshToken,
    isLoading,
    error,
    loginLimitInfo,
    // 計算屬性
    isAuthenticated,
    userEmail,
    isAdmin,
    // 方法
    register,
    login,
    logout,
    verifyEmail,
    resendVerification,
    clearError,
    saveTokens,
    clearTokens,
    initializeFromToken,
    resetLoginLimitInfo,
  }
})
