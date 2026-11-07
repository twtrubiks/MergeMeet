/**
 * JWT 工具測試
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { base64UrlDecode, decodeJwtPayload, isJwtExpired } from '@/utils/jwt'

const base64Url = (obj) =>
  btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')

const makeToken = (payload) => `header.${base64Url(payload)}.signature`

describe('jwt utils', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  describe('base64UrlDecode', () => {
    it('應能解碼未補 padding 的 base64url 字串', () => {
      // "ab" 的 base64 為 "YWI="，base64url 會去掉 "="
      expect(base64UrlDecode('YWI')).toBe('ab')
    })

    it('應把 - 與 _ 還原為 + 與 /', () => {
      const raw = String.fromCharCode(0xfb, 0xff)
      const standard = btoa(raw) // "+/8="
      const url = standard.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
      expect(base64UrlDecode(url)).toBe(raw)
    })
  })

  describe('decodeJwtPayload', () => {
    it('應解析出 payload 物件', () => {
      const token = makeToken({ sub: 'user-1', exp: 123 })
      expect(decodeJwtPayload(token)).toEqual({ sub: 'user-1', exp: 123 })
    })

    it('非字串、片段數不對或 payload 非 JSON 時回傳 null', () => {
      expect(decodeJwtPayload(null)).toBeNull()
      expect(decodeJwtPayload(undefined)).toBeNull()
      expect(decodeJwtPayload('only.two')).toBeNull()
      expect(decodeJwtPayload('a.!!!.c')).toBeNull()
      expect(decodeJwtPayload(`a.${btoa('not json')}.c`)).toBeNull()
    })
  })

  describe('isJwtExpired', () => {
    const nowSec = 1_700_000_000

    it('exp 在未來時為未過期', () => {
      vi.useFakeTimers()
      vi.setSystemTime(nowSec * 1000)
      expect(isJwtExpired(makeToken({ exp: nowSec + 60 }))).toBe(false)
    })

    it('exp 已過或剛好等於現在時為已過期', () => {
      vi.useFakeTimers()
      vi.setSystemTime(nowSec * 1000)
      expect(isJwtExpired(makeToken({ exp: nowSec - 1 }))).toBe(true)
      expect(isJwtExpired(makeToken({ exp: nowSec }))).toBe(true)
    })

    it('leewaySeconds 會把即將過期的 token 提前視為過期', () => {
      vi.useFakeTimers()
      vi.setSystemTime(nowSec * 1000)
      const token = makeToken({ exp: nowSec + 20 })
      expect(isJwtExpired(token)).toBe(false)
      expect(isJwtExpired(token, 30)).toBe(true)
    })

    it('沒有 exp 欄位視為未過期；無法解析或沒有 token 視為已過期', () => {
      expect(isJwtExpired(makeToken({ sub: 'x' }))).toBe(false)
      expect(isJwtExpired('garbage')).toBe(true)
      expect(isJwtExpired(null)).toBe(true)
    })
  })
})
