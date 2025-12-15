/**
 * API 客戶端配置
 *
 * 支援雙模式認證：
 * 1. HttpOnly Cookie + CSRF Token（優先）- Web 前端使用，防止 XSS
 * 2. Bearer Token（回退）- 向後兼容，API 客戶端 / 移動端使用
 */
import axios from 'axios'

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

    // 如果是 401 且還沒重試過，嘗試刷新 Token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // 嘗試刷新 Token（Cookie 模式會自動帶 refresh_token Cookie）
        const response = await axios.post('/api/auth/refresh', {}, {
          withCredentials: true,
        })

        // 刷新成功後，Cookie 已自動更新
        // 如果響應包含 Token（向後兼容），也存到 localStorage
        if (response.data.access_token) {
          localStorage.setItem('access_token', response.data.access_token)
        }
        if (response.data.refresh_token) {
          localStorage.setItem('refresh_token', response.data.refresh_token)
        }

        // 重新發送原本的請求
        return apiClient(originalRequest)
      } catch (refreshError) {
        // 刷新失敗，清除本地 Token 並跳轉到登入頁
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
