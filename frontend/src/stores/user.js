/**
 * 用戶狀態管理 (Pinia Store)
 *
 * TODO(Security): Token 目前儲存在 localStorage，存在 XSS 攻擊風險。
 * 建議改用 HttpOnly Cookie 存儲 Token：
 * - 後端設置 Set-Cookie: access_token=xxx; HttpOnly; Secure; SameSite=Strict
 * - 前端發送請求時使用 withCredentials: true
 * - 參考: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
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

    try {
      const response = await authAPI.login(credentials)
      saveTokens(response)

      // 從 Token 初始化用戶資訊（包含 user.id）
      initializeFromToken()

      return true
    } catch (err) {
      error.value = err.response?.data?.detail || '登入失敗'
      logger.error('登入錯誤:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 用戶登出
   */
  const logout = () => {
    clearTokens()
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
   * 從 JWT Token 解析用戶資料並初始化
   * 注意：會保留現有的 is_admin 屬性，避免管理員登入後狀態被覆蓋
   */
  const initializeFromToken = () => {
    if (!accessToken.value) {
      return
    }

    try {
      // 解析 JWT token (格式: header.payload.signature)
      const payload = accessToken.value.split('.')[1]
      const decodedPayload = JSON.parse(atob(payload))

      // 從 token 提取用戶資訊，保留現有的 is_admin 和 email 屬性
      if (decodedPayload.sub) {
        const currentIsAdmin = user.value?.is_admin || false
        const currentEmail = user.value?.email || null
        user.value = {
          id: decodedPayload.sub,
          email: decodedPayload.email || currentEmail,
          email_verified: decodedPayload.email_verified || false,
          is_admin: currentIsAdmin
        }
      }
    } catch (err) {
      logger.error('Failed to decode token:', err)
      // Token 無效，清除
      clearTokens()
    }
  }

  return {
    // 狀態
    user,
    accessToken,
    refreshToken,
    isLoading,
    error,
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
  }
})
