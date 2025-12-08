/**
 * 安全的日期格式化函數
 * 處理無效日期字符串和負數時間差
 *
 * @param {string} dateString - ISO 8601 日期字符串
 * @returns {string} 格式化後的日期字符串
 */
export function safeFormatDate(dateString) {
  // 1. 驗證輸入
  if (!dateString || typeof dateString !== 'string') {
    return ''
  }

  const date = new Date(dateString)

  // 2. 驗證日期有效性
  if (isNaN(date.getTime())) {
    return ''
  }

  const now = new Date()
  const diffInMs = Math.max(0, now - date)  // 避免負數 (服務器時間比客戶端快的情況)
  const diffMins = Math.floor(diffInMs / (1000 * 60))
  const diffHours = Math.floor(diffInMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return '剛剛'
  if (diffMins < 60) return `${diffMins} 分鐘前`
  if (diffHours < 24) return `${diffHours} 小時前`
  if (diffDays < 7) return `${diffDays} 天前`

  // 超過 7 天顯示完整日期
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

/**
 * 格式化配對日期 (擴展版本，用於 Matches.vue)
 *
 * @param {string} dateString - ISO 8601 日期字符串
 * @returns {string} 格式化後的日期字符串
 */
export function formatMatchDate(dateString) {
  // 驗證輸入
  if (!dateString || typeof dateString !== 'string') {
    return ''
  }

  const date = new Date(dateString)

  // 驗證日期有效性
  if (isNaN(date.getTime())) {
    return ''
  }

  const now = new Date()
  const diffInMs = Math.max(0, now - date)
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))

  if (diffInDays === 0) {
    return '今天'
  } else if (diffInDays === 1) {
    return '昨天'
  } else if (diffInDays < 7) {
    return `${diffInDays} 天前`
  } else if (diffInDays < 30) {
    const weeks = Math.floor(diffInDays / 7)
    return `${weeks} 週前`
  } else {
    return date.toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }
}
