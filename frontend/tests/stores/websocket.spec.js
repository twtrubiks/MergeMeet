/**
 * WebSocket Store 測試
 *
 * 重點：閒置超過 access token 效期後重連，必須先刷新 token 再認證，
 * 以及認證被拒、REST 刷新成功等情境下的重連行為。
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWebSocketStore, ConnectionState } from '@/stores/websocket'
import { useUserStore } from '@/stores/user'
import { refreshAuthToken, handleSessionExpired } from '@/api/client'

vi.mock('@/api/client', () => ({
  refreshAuthToken: vi.fn(),
  handleSessionExpired: vi.fn(() => Promise.resolve())
}))

vi.mock('@/api/auth', () => ({
  authAPI: { logout: vi.fn() }
}))

vi.mock('@/config', () => ({
  getWebSocketUrl: () => 'ws://localhost:8000/api/ws',
  API_BASE_URL: ''
}))

const base64Url = (obj) =>
  btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
const makeToken = (payload) => `header.${base64Url(payload)}.signature`

const USER_ID = 'user-1'
const nowSec = () => Math.floor(Date.now() / 1000)
const validToken = () => makeToken({ sub: USER_ID, exp: nowSec() + 1800 })
const expiredToken = () => makeToken({ sub: USER_ID, exp: nowSec() - 60 })

/** 等待 connect() 內部的非同步步驤走到建立 socket */
const waitForSocket = (store) => vi.waitFor(() => expect(store.socket).not.toBeNull())

/** 模擬伺服器端完成認證 */
const completeAuth = (store) => {
  store.socket.onopen()
  store.socket.onmessage({ data: JSON.stringify({ type: 'auth_success' }) })
}

/** 模擬 refreshAuthToken 成功：回傳新 token 並像真實實作一樣觸發 token-refreshed 事件 */
const mockRefreshSuccess = (newToken) => {
  refreshAuthToken.mockImplementation(() => {
    localStorage.setItem('access_token', newToken)
    window.dispatchEvent(new CustomEvent('token-refreshed', { detail: { access_token: newToken } }))
    return Promise.resolve({ data: { access_token: newToken } })
  })
}

const sentAuthToken = (store) => {
  const authCall = store.socket.send.mock.calls.find(([raw]) => JSON.parse(raw).type === 'auth')
  return authCall ? JSON.parse(authCall[0]).token : null
}

describe('WebSocket Store', () => {
  let userStore

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.getItem.mockReturnValue(null)
    vi.clearAllMocks()
    userStore = useUserStore()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  const loginWith = (token) => {
    userStore.saveTokens({ access_token: token })
    userStore.initializeFromToken()
  }

  describe('connect：連線前的 token 檢查', () => {
    it('token 仍有效時不刷新，直接用原 token 認證', async () => {
      const token = validToken()
      loginWith(token)
      const store = useWebSocketStore()

      const connecting = store.connect()
      await waitForSocket(store)
      completeAuth(store)
      await connecting

      expect(refreshAuthToken).not.toHaveBeenCalled()
      expect(sentAuthToken(store)).toBe(token)
      expect(store.connectionState).toBe(ConnectionState.CONNECTED)
      expect(store.reconnectAttempts).toBe(0)
    })

    it('token 已過期時先刷新，再用新 token 認證', async () => {
      loginWith(expiredToken())
      const newToken = validToken()
      mockRefreshSuccess(newToken)
      const store = useWebSocketStore()

      const connecting = store.connect()
      await waitForSocket(store)
      completeAuth(store)
      await connecting

      expect(refreshAuthToken).toHaveBeenCalledTimes(1)
      expect(sentAuthToken(store)).toBe(newToken)
      expect(store.connectionState).toBe(ConnectionState.CONNECTED)
    })

    it('token 將在 30 秒內過期也視為需要刷新', async () => {
      loginWith(makeToken({ sub: USER_ID, exp: nowSec() + 10 }))
      const newToken = validToken()
      mockRefreshSuccess(newToken)
      const store = useWebSocketStore()

      const connecting = store.connect()
      await waitForSocket(store)
      completeAuth(store)
      await connecting

      expect(refreshAuthToken).toHaveBeenCalledTimes(1)
      expect(sentAuthToken(store)).toBe(newToken)
    })

    it('刷新回 401（refresh token 也失效）時走 session 過期流程，不排程重連', async () => {
      vi.useFakeTimers()
      loginWith(expiredToken())
      refreshAuthToken.mockRejectedValue({ response: { status: 401 } })
      const store = useWebSocketStore()

      await expect(store.connect()).rejects.toMatchObject({ response: { status: 401 } })

      expect(handleSessionExpired).toHaveBeenCalledTimes(1)
      expect(store.reconnectAttempts).toBe(0)
      expect(store.connectionState).toBe(ConnectionState.DISCONNECTED)
      expect(store.socket).toBeNull()
    })

    it('刷新因網路錯誤失敗時排程重連，之後重試會再次刷新', async () => {
      vi.useFakeTimers()
      loginWith(expiredToken())
      refreshAuthToken.mockRejectedValueOnce(new Error('Network Error'))
      const store = useWebSocketStore()

      await expect(store.connect()).rejects.toThrow('Network Error')

      expect(handleSessionExpired).not.toHaveBeenCalled()
      expect(store.reconnectAttempts).toBe(1)
      expect(store.connectionState).toBe(ConnectionState.DISCONNECTED)

      // 重連計時器到期 → 再次 connect → 再次嘗試刷新
      mockRefreshSuccess(validToken())
      await vi.advanceTimersByTimeAsync(2000)
      expect(refreshAuthToken).toHaveBeenCalledTimes(2)
      expect(store.socket).not.toBeNull()
    })

    it('沒有 token 時拒絕連線', async () => {
      const store = useWebSocketStore()
      await expect(store.connect()).rejects.toThrow('User not authenticated')
      expect(refreshAuthToken).not.toHaveBeenCalled()
    })
  })

  describe('認證階段被伺服器關閉', () => {
    it('認證前收到關閉（1008）：reject、排程重連，且下一次連線強制刷新 token', async () => {
      vi.useFakeTimers()
      const token = validToken()
      loginWith(token)
      const store = useWebSocketStore()

      const connecting = store.connect()
      await waitForSocket(store)
      store.socket.onopen()
      // 後端驗證 token 失敗，以 1008 關閉
      store.socket.onclose({ code: 1008, reason: 'Authentication failed' })

      await expect(connecting).rejects.toThrow('closed before auth')
      expect(store.connectionState).toBe(ConnectionState.DISCONNECTED)
      expect(store.reconnectAttempts).toBe(1)
      expect(refreshAuthToken).not.toHaveBeenCalled()

      // 重連：即使本地 token 看起來未過期，也要先刷新（伺服器可能已撤銷）
      const newToken = validToken() + 'new'
      mockRefreshSuccess(newToken)
      await vi.advanceTimersByTimeAsync(2000)
      await waitForSocket(store)

      expect(refreshAuthToken).toHaveBeenCalledTimes(1)
      expect(store.connectionState).toBe(ConnectionState.RECONNECTING)
      store.socket.onopen()
      expect(sentAuthToken(store)).toBe(newToken)
    })

    it('認證前以 1000 關閉（舊版後端行為）也視為異常並重連', async () => {
      vi.useFakeTimers()
      loginWith(validToken())
      const store = useWebSocketStore()

      const connecting = store.connect()
      await waitForSocket(store)
      store.socket.onopen()
      store.socket.onclose({ code: 1000, reason: '' })

      await expect(connecting).rejects.toThrow('closed before auth')
      expect(store.reconnectAttempts).toBe(1)
    })

    it('認證成功後正常關閉（1000）不重連', async () => {
      loginWith(validToken())
      const store = useWebSocketStore()

      const connecting = store.connect()
      await waitForSocket(store)
      const socket = store.socket
      completeAuth(store)
      await connecting

      socket.onclose({ code: 1000, reason: 'Client disconnect' })
      expect(store.reconnectAttempts).toBe(0)
      expect(store.connectionState).toBe(ConnectionState.DISCONNECTED)
    })

    it('認證成功後異常斷線（1006）會排程重連', async () => {
      vi.useFakeTimers()
      loginWith(validToken())
      const store = useWebSocketStore()

      const connecting = store.connect()
      await waitForSocket(store)
      const socket = store.socket
      completeAuth(store)
      await connecting

      socket.onclose({ code: 1006, reason: '' })
      expect(store.reconnectAttempts).toBe(1)
    })
  })

  describe('token-refreshed 事件', () => {
    it('WS 已斷線且重試已放棄時，REST 刷新成功會重設重試次數並重新連線', async () => {
      vi.useFakeTimers()
      const token = validToken()
      loginWith(token)
      const store = useWebSocketStore()
      store.initAutoConnect()

      // initAutoConnect 的 immediate watch 會發起連線，先讓它完成
      await waitForSocket(store)
      const socket = store.socket
      completeAuth(store)
      await vi.waitFor(() => expect(store.connectionState).toBe(ConnectionState.CONNECTED))

      // 模擬「重試已放棄」：disconnect() 會把 reconnectAttempts 推到上限
      socket.onclose({ code: 1006, reason: '' })
      store.disconnect()
      expect(store.connectionState).toBe(ConnectionState.DISCONNECTED)
      const attemptsBefore = store.reconnectAttempts
      expect(attemptsBefore).toBeGreaterThan(0)

      // REST 流程刷新 token 成功
      const newToken = validToken() + 'rest'
      userStore.saveTokens({ access_token: newToken })
      window.dispatchEvent(
        new CustomEvent('token-refreshed', { detail: { access_token: newToken } })
      )

      await waitForSocket(store)
      store.socket.onopen()
      expect(sentAuthToken(store)).toBe(newToken)
      store.socket.onmessage({ data: JSON.stringify({ type: 'auth_success' }) })
      expect(store.connectionState).toBe(ConnectionState.CONNECTED)
      expect(store.reconnectAttempts).toBe(0)
    })

    it('WS 連線中或已連線時忽略 token-refreshed', async () => {
      loginWith(validToken())
      const store = useWebSocketStore()
      store.initAutoConnect()

      await waitForSocket(store)
      const socket = store.socket
      completeAuth(store)
      await vi.waitFor(() => expect(store.connectionState).toBe(ConnectionState.CONNECTED))

      window.dispatchEvent(
        new CustomEvent('token-refreshed', { detail: { access_token: validToken() } })
      )
      await Promise.resolve()

      // 仍是同一條 socket，沒有重建
      expect(store.socket).toBe(socket)
      expect(store.connectionState).toBe(ConnectionState.CONNECTED)
    })

    it('登出後（沒有 token）忽略 token-refreshed', async () => {
      loginWith(validToken())
      const store = useWebSocketStore()
      store.initAutoConnect()
      await waitForSocket(store)
      completeAuth(store)
      await vi.waitFor(() => expect(store.connectionState).toBe(ConnectionState.CONNECTED))

      userStore.clearTokens()
      await vi.waitFor(() => expect(store.connectionState).toBe(ConnectionState.DISCONNECTED))

      window.dispatchEvent(new CustomEvent('token-refreshed', { detail: { access_token: null } }))
      await Promise.resolve()

      expect(store.socket).toBeNull()
      expect(store.connectionState).toBe(ConnectionState.DISCONNECTED)
    })
  })
})
