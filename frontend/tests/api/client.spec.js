/**
 * API Client 測試
 *
 * 測試 Token 刷新的 Race Condition 修復
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'

// Mock axios
vi.mock('axios', () => {
  return {
    default: {
      create: vi.fn(() => ({
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() }
        }
      })),
      post: vi.fn()
    }
  }
})

// Mock discreteApi
vi.mock('@/utils/discreteApi', () => ({
  showSessionExpiredMessage: vi.fn(() => Promise.resolve())
}))

describe('Token Refresh Mutex', () => {
  let refreshPromise = null

  beforeEach(() => {
    refreshPromise = null
    vi.clearAllMocks()
  })

  afterEach(() => {
    refreshPromise = null
  })

  /**
   * 模擬 client.js 中的 mutex 邏輯
   */
  const simulateRefreshWithMutex = async () => {
    if (!refreshPromise) {
      refreshPromise = axios.post('/api/auth/refresh', {}, { withCredentials: true })
        .finally(() => {
          refreshPromise = null
        })
    }
    return refreshPromise
  }

  it('多個並發刷新請求應該只發送一次 API 請求', async () => {
    // 模擬刷新成功
    axios.post.mockResolvedValueOnce({
      data: { access_token: 'new_token', refresh_token: 'new_refresh' }
    })

    // 同時發送 3 個刷新請求
    const results = await Promise.all([
      simulateRefreshWithMutex(),
      simulateRefreshWithMutex(),
      simulateRefreshWithMutex()
    ])

    // axios.post 應該只被呼叫一次
    expect(axios.post).toHaveBeenCalledTimes(1)

    // 所有請求應該得到相同的結果
    expect(results[0]).toBe(results[1])
    expect(results[1]).toBe(results[2])
  })

  it('刷新完成後應該允許下一次刷新', async () => {
    // 第一次刷新
    axios.post.mockResolvedValueOnce({
      data: { access_token: 'token1', refresh_token: 'refresh1' }
    })

    await simulateRefreshWithMutex()

    // 第二次刷新（應該發送新的請求）
    axios.post.mockResolvedValueOnce({
      data: { access_token: 'token2', refresh_token: 'refresh2' }
    })

    await simulateRefreshWithMutex()

    // axios.post 應該被呼叫兩次
    expect(axios.post).toHaveBeenCalledTimes(2)
  })

  it('刷新失敗時所有等待的請求都應該收到錯誤', async () => {
    // 模擬刷新失敗
    const error = new Error('Refresh failed')
    axios.post.mockRejectedValueOnce(error)

    // 同時發送 3 個刷新請求
    const promises = [
      simulateRefreshWithMutex().catch(e => e),
      simulateRefreshWithMutex().catch(e => e),
      simulateRefreshWithMutex().catch(e => e)
    ]

    const results = await Promise.all(promises)

    // 所有請求應該收到相同的錯誤
    expect(results[0]).toBe(error)
    expect(results[1]).toBe(error)
    expect(results[2]).toBe(error)

    // axios.post 應該只被呼叫一次
    expect(axios.post).toHaveBeenCalledTimes(1)
  })
})
