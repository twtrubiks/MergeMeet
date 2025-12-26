/**
 * API 客戶端配置
 *
 * 支援雙模式認證：
 * 1. HttpOnly Cookie + CSRF Token（優先）- Web 前端使用，防止 XSS
 * 2. Bearer Token（回退）- 向後兼容，API 客戶端 / 移動端使用
 */
import axios from 'axios'
import { showSessionExpiredMessage } from '@/utils/discreteApi'

/**
 * 從 Cookie 中獲取指定的值
 * @param {string} name - Cookie 名稱
 * @returns {string|null} Cookie 值
 */
function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return null
}

/**
 * Token 刷新 Mutex
 *
 * 防止多個請求同時刷新 Token 導致 Race Condition：
 * - 當多個請求同時收到 401 時，只有第一個會執行刷新
 * - 其他請求等待刷新完成後重試
 * - 避免 Token Rotation 機制導致舊 Token 被 blacklist 後第二個刷新失敗
 *
 * 修復：commit 598c2d0 之後發現的 Race Condition bug
 */
let refreshPromise = null
let isRedirectingToLogin = false

// 建立 axios 實例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  withCredentials: true, // 允許 Cookie 跨域傳送
  headers: {
    'Content-Type': 'application/json',
  },
})

// 請求攔截器：自動注入 Token
apiClient.interceptors.request.use(
  (config) => {
    // 1. 優先注入 CSRF Token（Cookie 認證模式）
    const csrfToken = getCookie('csrf_token')
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken
    }

    // 2. 如果沒有 CSRF Token（Cookie 模式未啟用），回退到 Bearer Token
    //    這提供向後兼容，支援開發過渡期
    const accessToken = localStorage.getItem('access_token')
    if (!csrfToken && accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 回應攔截器：處理錯誤和 Token 刷新
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // 登入相關 API 不需要 Token 刷新（這些 API 本身就是獲取 Token 的）
    const authEndpoints = ['/auth/login', '/auth/register', '/auth/admin-login']
    const isAuthEndpoint = authEndpoints.some(endpoint => originalRequest.url?.includes(endpoint))

    // 如果是 401 且還沒重試過，且不是登入相關 API，嘗試刷新 Token
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true

      try {
        // Mutex：如果已經有刷新請求在進行，等待它完成
        // 這樣可以避免多個請求同時刷新導致 Token Rotation 失敗
        if (!refreshPromise) {
          refreshPromise = axios.post('/api/auth/refresh', {}, {
            withCredentials: true,
          }).finally(() => {
            // 刷新完成後清除 Promise，允許下次刷新
            refreshPromise = null
          })
        }

        const response = await refreshPromise

        // 刷新成功後，Cookie 已自動更新
        // 如果響應包含 Token（向後兼容），也存到 localStorage
        if (response.data.access_token) {
          localStorage.setItem('access_token', response.data.access_token)
        }
        if (response.data.refresh_token) {
          localStorage.setItem('refresh_token', response.data.refresh_token)
        }

        // 通知 Pinia Store 更新狀態（避免循環依賴，使用 CustomEvent）
        window.dispatchEvent(new CustomEvent('token-refreshed', {
          detail: {
            access_token: response.data.access_token,
            refresh_token: response.data.refresh_token
          }
        }))

        // 重新發送原本的請求
        return apiClient(originalRequest)
      } catch (refreshError) {
        // 刷新失敗，清除本地 Token
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')

        // 只有第一個失敗的請求顯示提示並跳轉
        // 避免多個請求同時跳轉造成多次提示
        if (!isRedirectingToLogin) {
          isRedirectingToLogin = true
          await showSessionExpiredMessage()
          window.location.href = '/login'
        }

        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
