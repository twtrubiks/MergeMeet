/**
 * Router Guard 測試：過期 access token 的靜默續期
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { refreshAuthToken } from '@/api/client'

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal()
  // jsdom 下 tests/setup.js 把 window.location 換成純物件，改用 memory history
  return { ...actual, createWebHistory: () => actual.createMemoryHistory() }
})

vi.mock('@/api/client', () => ({
  refreshAuthToken: vi.fn(),
  handleSessionExpired: vi.fn()
}))

vi.mock('@/utils/discreteApi', () => ({
  discreteMessage: { warning: vi.fn() }
}))

vi.mock('@/stores/profile', () => ({
  useProfileStore: () => ({ hasProfile: true, isProfileComplete: true, fetchProfile: vi.fn() })
}))

vi.mock('@/views/Home.vue', () => ({ default: { template: '<div>home</div>' } }))
vi.mock('@/views/Login.vue', () => ({ default: { template: '<div>login</div>' } }))

function makeToken(expOffsetSeconds) {
  const payload = {
    sub: 'user-1',
    email: 'u@example.com',
    email_verified: true,
    exp: Math.floor(Date.now() / 1000) + expOffsetSeconds
  }
  const b64 = (obj) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(payload)}.sig`
}

const EXPIRED_TOKEN = makeToken(-12 * 3600)
const FRESH_TOKEN = makeToken(1800)

/** 模擬 refreshAuthToken 成功時 client.js 的行為：廣播 token-refreshed */
function refreshSucceeds() {
  refreshAuthToken.mockImplementation(async () => {
    window.dispatchEvent(
      new CustomEvent('token-refreshed', { detail: { access_token: FRESH_TOKEN } })
    )
    return { data: { access_token: FRESH_TOKEN } }
  })
}

describe('Router Guard：靜默續期', () => {
  let router
  let userStore

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.resetModules()
    setActivePinia(createPinia())

    localStorage.getItem.mockImplementation((key) =>
      key === 'access_token' ? EXPIRED_TOKEN : null
    )

    router = (await import('@/router')).default
    userStore = (await import('@/stores/user')).useUserStore()
  })

  it('公開頁（首頁）重整時 token 已過期 → 仍會靜默續期並恢復登入狀態', async () => {
    refreshSucceeds()

    await router.push('/')

    expect(refreshAuthToken).toHaveBeenCalledTimes(1)
    expect(userStore.isAuthenticated).toBe(true)
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('受保護頁續期成功 → 放行', async () => {
    refreshSucceeds()

    await router.push('/settings')

    expect(refreshAuthToken).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.path).toBe('/settings')
  })

  it('續期回 401 → 清除殘留 token 並導向登入頁', async () => {
    refreshAuthToken.mockRejectedValue({ response: { status: 401 } })

    await router.push('/settings')

    expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('續期遇網路錯誤（無 response）→ 保留 token 供下次重試，但本次導向登入頁', async () => {
    refreshAuthToken.mockRejectedValue(new Error('Network Error'))

    await router.push('/settings')

    expect(localStorage.removeItem).not.toHaveBeenCalledWith('access_token')
    expect(userStore.accessToken).toBe(EXPIRED_TOKEN)
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('續期回 5xx → 保留 token', async () => {
    refreshAuthToken.mockRejectedValue({ response: { status: 503 } })

    await router.push('/settings')

    expect(localStorage.removeItem).not.toHaveBeenCalledWith('access_token')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('localStorage 沒有 token → 不嘗試續期，受保護頁直接導向登入頁', async () => {
    localStorage.getItem.mockReturnValue(null)
    setActivePinia(createPinia())
    router = (await import('@/router')).default

    await router.push('/settings')

    expect(refreshAuthToken).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/login')
  })
})
