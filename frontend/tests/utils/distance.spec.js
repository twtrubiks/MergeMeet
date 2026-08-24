/**
 * 距離顯示工具測試
 */
import { describe, it, expect } from 'vitest'
import { formatDistance, isNearby } from '@/utils/distance'

describe('formatDistance', () => {
  it('同一座標（0 公里）顯示「附近」，而非 0m', () => {
    // 回歸測試：後端曾用 falsy 判斷把 0.0 丟成 null，導致距離完全不顯示
    expect(formatDistance(0)).toBe('附近')
  })

  it('極近距離模糊化為「附近」', () => {
    expect(formatDistance(0.05)).toBe('附近')
  })

  it('1 公里內以公尺顯示', () => {
    expect(formatDistance(0.1)).toBe('100m')
    expect(formatDistance(0.8)).toBe('800m')
  })

  it('10 公里內保留一位小數', () => {
    expect(formatDistance(2.44)).toBe('2.4km')
    expect(formatDistance(9.9)).toBe('9.9km')
  })

  it('10 公里以上取整數', () => {
    expect(formatDistance(10)).toBe('10km')
    expect(formatDistance(133.32)).toBe('133km')
  })

  it('無距離資料時回傳空字串', () => {
    expect(formatDistance(null)).toBe('')
    expect(formatDistance(undefined)).toBe('')
  })
})

describe('isNearby', () => {
  it('0 公里算「附近」', () => {
    expect(isNearby(0)).toBe(true)
  })

  it('達到門檻就不算「附近」', () => {
    expect(isNearby(0.1)).toBe(false)
    expect(isNearby(3)).toBe(false)
  })

  it('無距離資料不算「附近」', () => {
    // 沒有位置資料 ≠ 就在附近，兩者不可混為一談
    expect(isNearby(null)).toBe(false)
    expect(isNearby(undefined)).toBe(false)
  })
})
