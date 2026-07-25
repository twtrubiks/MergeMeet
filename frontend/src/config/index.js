/**
 * 前端環境設定唯一出口
 *
 * 預設採同源相對路徑：dev 由 Vite proxy 轉發（見 vite.config.js），
 * prod 由反向代理轉發，無需設定任何環境變數。
 * 僅在前後端拆網域部署時，才透過 .env 的 VITE_* 變數覆寫（見 .env.example）。
 *
 * 禁止在其他檔案直接寫死 localhost 或讀取 import.meta.env。
 */

/** API 基礎路徑 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

/** 媒體檔案基礎網址；同源部署時為空字串，直接使用後端回傳的相對路徑 */
export const MEDIA_BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL || ''

/**
 * 取得 WebSocket 連線網址
 * @returns {string} 完整的 ws(s):// 網址
 */
export function getWebSocketUrl() {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

/**
 * 將後端回傳的媒體路徑轉為可顯示的網址
 * @param {string} url - 後端回傳的路徑（相對路徑或完整網址）
 * @returns {string} 可用於 <img src> 的網址
 */
export function getMediaUrl(url) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${MEDIA_BASE_URL}${url}`
}
