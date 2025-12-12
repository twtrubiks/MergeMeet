/**
 * 認證相關 API
 */
import apiClient from './client'

export const authAPI = {
  /**
   * 用戶註冊
   * @param {Object} data - 註冊資料
   * @param {string} data.email - Email
   * @param {string} data.password - 密碼
   * @param {string} data.date_of_birth - 出生日期 (YYYY-MM-DD)
   * @returns {Promise} 包含 access_token 和 refresh_token
   */
  async register(data) {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  },

  /**
   * 用戶登入
   * @param {Object} credentials - 登入憑證
   * @param {string} credentials.email - Email
   * @param {string} credentials.password - 密碼
   * @returns {Promise} 包含 success 狀態、data 或錯誤資訊（含登入限制資訊）
   */
  async login(credentials) {
    try {
      const response = await apiClient.post('/auth/login', credentials)
      return { success: true, data: response.data }
    } catch (err) {
      // 解析登入限制相關的 headers
      const headers = err.response?.headers || {}
      const remainingAttempts = parseInt(headers['x-ratelimit-remaining'], 10)
      const lockoutSeconds = parseInt(headers['x-lockout-seconds'], 10)

      return {
        success: false,
        error: err.response?.data?.detail || '登入失敗',
        remainingAttempts: isNaN(remainingAttempts) ? null : remainingAttempts,
        lockoutSeconds: isNaN(lockoutSeconds) ? 0 : lockoutSeconds,
        isLocked: err.response?.status === 429
      }
    }
  },

  /**
   * 刷新 Access Token
   * @param {string} refreshToken - Refresh Token
   * @returns {Promise} 新的 Token
   */
  async refreshToken(refreshToken) {
    const response = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  /**
   * 驗證 Email
   * @param {Object} data - 驗證資料
   * @param {string} data.email - Email
   * @param {string} data.verification_code - 驗證碼
   * @returns {Promise}
   */
  async verifyEmail(data) {
    const response = await apiClient.post('/auth/verify-email', data)
    return response.data
  },

  /**
   * 重新發送驗證碼
   * @param {string} email - Email
   * @returns {Promise}
   */
  async resendVerification(email) {
    const response = await apiClient.post('/auth/resend-verification', null, {
      params: { email },
    })
    return response.data
  },
}
