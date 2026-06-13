/**
 * discreteApi 測試
 *
 * 測試速率限制提示（showRateLimitMessage）的訊息內容與節流邏輯
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// vi.hoisted：讓 mock 函數與被提升的 vi.mock 一同初始化
const { warningMock } = vi.hoisted(() => ({ warningMock: vi.fn() }))

// Mock Naive UI discrete API（避免在測試環境掛載真實 DOM）
vi.mock('naive-ui', () => ({
  createDiscreteApi: () => ({ message: { warning: warningMock } })
}))

import { showRateLimitMessage } from '@/utils/discreteApi'

describe('showRateLimitMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('帶 Retry-After 秒數時，訊息包含等待秒數', () => {
    vi.setSystemTime(10_000)
    showRateLimitMessage('5')

    expect(warningMock).toHaveBeenCalledTimes(1)
    expect(warningMock.mock.calls[0][0]).toContain('5 秒')
  })

  it('未帶秒數時，顯示「請稍後再試」', () => {
    vi.setSystemTime(20_000)
    showRateLimitMessage()

    expect(warningMock).toHaveBeenCalledTimes(1)
    expect(warningMock.mock.calls[0][0]).toContain('請稍後再試')
  })

  it('3 秒內重複觸發只顯示一次（節流，避免並發請求洗版）', () => {
    vi.setSystemTime(30_000)
    showRateLimitMessage('3')
    showRateLimitMessage('3')
    showRateLimitMessage('3')

    expect(warningMock).toHaveBeenCalledTimes(1)

    // 超過節流窗口後可再次顯示
    vi.setSystemTime(34_000)
    showRateLimitMessage('3')
    expect(warningMock).toHaveBeenCalledTimes(2)
  })
})
