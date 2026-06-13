/**
 * Naive UI Discrete API
 * 用於在 Vue 組件外（如 axios 攔截器）顯示 UI 提示
 */
import { createDiscreteApi } from 'naive-ui'

const { message } = createDiscreteApi(['message'], {
  messageProviderProps: {
    placement: 'top',
    duration: 3000,
    keepAliveOnHover: true
  }
})

/**
 * 顯示 Session 過期提示
 * @returns {Promise<void>} 訊息顯示完成後 resolve
 */
export const showSessionExpiredMessage = () => {
  return new Promise((resolve) => {
    message.warning('登入已過期，請重新登入', {
      duration: 2000,
      closable: true
    })
    setTimeout(resolve, 2000)
  })
}

// 速率限制提示節流：避免並發請求同時觸發 429 時洗版
let lastRateLimitShownAt = 0

/**
 * 顯示速率限制提示（後端回傳 429 時）
 * @param {string|number} [retryAfterSeconds] - Retry-After header 值（秒）
 */
export const showRateLimitMessage = (retryAfterSeconds) => {
  // 3 秒內僅顯示一次
  const now = Date.now()
  if (now - lastRateLimitShownAt < 3000) return
  lastRateLimitShownAt = now

  const seconds = Number(retryAfterSeconds)
  const suffix = seconds > 0 ? `，請 ${seconds} 秒後再試` : '，請稍後再試'
  message.warning(`請求過於頻繁${suffix}`, {
    duration: 3000,
    closable: true
  })
}

export { message as discreteMessage }
