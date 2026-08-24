/**
 * 距離顯示工具
 */

// 小於此距離視為「附近」（後端距離四捨五入到 0.1km，同址會得到 0）
const NEARBY_THRESHOLD_KM = 0.1

/**
 * 是否近到該用模糊描述取代精確距離
 *
 * 同一座標會算出 0 公里，直接顯示「0m」既奇怪又等於昭告雙方在同一個點上，
 * 因此極近距離一律模糊化。
 *
 * @param {number|null|undefined} km
 * @returns {boolean}
 */
export function isNearby(km) {
  return km !== null && km !== undefined && km < NEARBY_THRESHOLD_KM
}

/**
 * 格式化距離顯示
 *
 * 後端在無位置資料時回傳 null（不是 0），呼叫端請用 `!= null` 判斷是否有距離，
 * 別用 falsy 判斷——0 公里是合法距離。
 *
 * @param {number|null|undefined} km
 * @returns {string} 例：'附近'、'800m'、'2.4km'、'133km'；無距離時為空字串
 */
export function formatDistance(km) {
  if (km === null || km === undefined) return ''
  if (isNearby(km)) return '附近'
  if (km < 1) return `${Math.round(km * 1000)}m`
  if (km < 10) return `${km.toFixed(1)}km`
  return `${Math.round(km)}km`
}
