/**
 * 通用工具函數
 */

/**
 * 防抖函數 - 延遲執行，重複調用會重置計時器
 * 適用於：搜尋輸入、表單驗證
 *
 * @param {Function} fn - 要執行的函數
 * @param {number} delay - 延遲時間（毫秒）
 * @returns {Function} 防抖後的函數
 */
export function debounce(fn, delay = 300) {
  let timeoutId = null

  const debouncedFn = function (...args) {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }

    timeoutId = setTimeout(() => {
      fn.apply(this, args)
      timeoutId = null
    }, delay)
  }

  // 提供取消方法
  debouncedFn.cancel = function () {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  return debouncedFn
}

/**
 * 節流函數 - 固定時間內只執行一次
 * 適用於：按鈕點擊、滾動事件
 *
 * @param {Function} fn - 要執行的函數
 * @param {number} limit - 時間間隔（毫秒）
 * @returns {Function} 節流後的函數
 */
export function throttle(fn, limit = 300) {
  let inThrottle = false

  return function (...args) {
    if (!inThrottle) {
      fn.apply(this, args)
      inThrottle = true
      setTimeout(() => {
        inThrottle = false
      }, limit)
    }
  }
}

/**
 * 防止重複點擊的裝飾器
 * 適用於：API 請求按鈕
 *
 * @param {Function} fn - 異步函數
 * @returns {Function} 包裝後的函數
 */
export function preventDoubleClick(fn) {
  let isProcessing = false

  return async function (...args) {
    if (isProcessing) {
      return
    }

    isProcessing = true
    try {
      return await fn.apply(this, args)
    } finally {
      isProcessing = false
    }
  }
}

/**
 * 帶狀態的防重複點擊 composable
 * 適用於：需要顯示 loading 狀態的按鈕
 *
 * @returns {Object} { isLoading, execute }
 */
export function useAsyncAction() {
  let isLoading = false

  const execute = async (fn) => {
    if (isLoading) {
      return
    }

    isLoading = true
    try {
      return await fn()
    } finally {
      isLoading = false
    }
  }

  return { isLoading, execute }
}
