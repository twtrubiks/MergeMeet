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

export { message as discreteMessage }
