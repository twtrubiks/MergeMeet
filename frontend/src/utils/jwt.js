/**
 * JWT 工具
 *
 * 僅做前端的「可讀性」解析（不驗證簽章），用於：
 * - 從 access token 取出 sub / email / is_admin 等資訊
 * - 在送出請求或建立 WebSocket 前，預先判斷 token 是否已過期
 */

/**
 * Base64URL 解碼
 * @param {string} str - Base64URL 編碼的字串
 * @returns {string} 解碼後的字串
 */
export const base64UrlDecode = (str) => {
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/')
  const pad = base64.length % 4
  if (pad) {
    base64 += '='.repeat(4 - pad)
  }
  return atob(base64)
}

/**
 * 解析 JWT payload
 * @param {string|null|undefined} token - JWT 字串
 * @returns {object|null} payload 物件；格式錯誤時回傳 null
 */
export const decodeJwtPayload = (token) => {
  if (typeof token !== 'string') return null
  const parts = token.split('.')
  if (parts.length !== 3) return null
  try {
    return JSON.parse(base64UrlDecode(parts[1]))
  } catch {
    return null
  }
}

/**
 * 判斷 JWT 是否已過期（或即將過期）
 *
 * @param {string|null|undefined} token - JWT 字串
 * @param {number} leewaySeconds - 提前視為過期的秒數（預設 0）。
 *   建立 WebSocket 等「拿到 token 後還要一段時間才送到伺服器」的情境可給一點緩衝。
 * @returns {boolean} true 表示已過期、無法解析或沒有 token；payload 沒有 exp 欄位則視為未過期
 */
export const isJwtExpired = (token, leewaySeconds = 0) => {
  const payload = decodeJwtPayload(token)
  if (!payload) return true
  if (!payload.exp) return false
  return Date.now() >= (payload.exp - leewaySeconds) * 1000
}
