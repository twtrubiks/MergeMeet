/**
 * Profile Store 單元測試
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProfileStore } from '@/stores/profile'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

const makePhoto = (overrides = {}) => ({
  id: 'photo-1',
  url: '/uploads/photo-1.jpg',
  display_order: 0,
  is_profile_picture: false,
  moderation_status: 'APPROVED',
  rejection_reason: null,
  ...overrides
})

describe('Profile Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('照片 getters', () => {
    it('visiblePhotos 應該過濾掉 REJECTED 照片', () => {
      const store = useProfileStore()
      store.profile = {
        photos: [
          makePhoto({ id: 'p1', is_profile_picture: true }),
          makePhoto({ id: 'p2', moderation_status: 'PENDING' }),
          makePhoto({ id: 'p3', moderation_status: 'REJECTED', rejection_reason: '垃圾內容' })
        ]
      }

      expect(store.visiblePhotos.map((p) => p.id)).toEqual(['p1', 'p2'])
      expect(store.rejectedPhotosCount).toBe(1)
    })

    it('沒有駁回照片時 rejectedPhotosCount 應為 0', () => {
      const store = useProfileStore()
      store.profile = {
        photos: [makePhoto({ id: 'p1' }), makePhoto({ id: 'p2', moderation_status: 'PENDING' })]
      }

      expect(store.visiblePhotos).toHaveLength(2)
      expect(store.rejectedPhotosCount).toBe(0)
    })

    it('profile 為 null 時應回傳空清單', () => {
      const store = useProfileStore()

      expect(store.visiblePhotos).toEqual([])
      expect(store.rejectedPhotosCount).toBe(0)
      expect(store.profilePicture).toBeNull()
    })

    it('profilePicture 應優先使用主頭像', () => {
      const store = useProfileStore()
      store.profile = {
        photos: [
          makePhoto({ id: 'p1', url: '/uploads/p1.jpg' }),
          makePhoto({ id: 'p2', url: '/uploads/p2.jpg', is_profile_picture: true })
        ]
      }

      expect(store.profilePicture).toBe('/uploads/p2.jpg')
    })

    it('profilePicture 不應回退到 REJECTED 照片的 url', () => {
      const store = useProfileStore()
      store.profile = {
        photos: [
          makePhoto({ id: 'p1', url: '/uploads/p1.jpg', moderation_status: 'REJECTED' }),
          makePhoto({ id: 'p2', url: '/uploads/p2.jpg' })
        ]
      }

      expect(store.profilePicture).toBe('/uploads/p2.jpg')
    })

    it('所有照片皆被駁回時 profilePicture 應為 null', () => {
      const store = useProfileStore()
      store.profile = {
        photos: [
          makePhoto({ id: 'p1', moderation_status: 'REJECTED', is_profile_picture: true }),
          makePhoto({ id: 'p2', moderation_status: 'REJECTED' })
        ]
      }

      expect(store.profilePicture).toBeNull()
      expect(store.visiblePhotos).toEqual([])
      expect(store.rejectedPhotosCount).toBe(2)
    })
  })
})
