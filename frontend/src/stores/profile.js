/**
 * Profile Store
 * 管理個人檔案相關狀態和 API 呼叫
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api/client'

export const useProfileStore = defineStore('profile', () => {
  // State
  const profile = ref(null)
  const interestTags = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const hasProfile = computed(() => profile.value !== null)
  const isProfileComplete = computed(() => profile.value?.is_complete || false)
  const profilePhotos = computed(() => profile.value?.photos || [])
  const profileInterests = computed(() => profile.value?.interests || [])
  const profilePicture = computed(() => {
    const photos = profile.value?.photos || []
    const mainPhoto = photos.find(p => p.is_profile_picture)
    return mainPhoto?.url || photos[0]?.url || null
  })

  /**
   * 取得自己的個人檔案
   */
  const fetchProfile = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/api/profile')
      profile.value = response.data
      return response.data
    } catch (err) {
      if (err.response?.status === 404) {
        // 檔案不存在是正常情況
        profile.value = null
      } else {
        error.value = err.response?.data?.detail || '無法取得個人檔案'
        throw err
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 建立個人檔案
   * @param {Object} data - 檔案資料
   * @param {string} data.display_name - 顯示名稱
   * @param {string} data.gender - 性別 ('male', 'female', 'non_binary', 'prefer_not_to_say')
   * @param {string} data.bio - 個人簡介
   * @param {Object} data.location - 地理位置 { latitude, longitude, location_name }
   */
  const createProfile = async (data) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post('/api/profile', data)
      profile.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '建立個人檔案失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新個人檔案
   * @param {Object} data - 要更新的欄位
   */
  const updateProfile = async (data) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.patch('/api/profile', data)
      profile.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '更新個人檔案失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新興趣標籤
   * @param {Array<string>} interestIds - 興趣標籤 ID 陣列 (3-10 個)
   */
  const updateInterests = async (interestIds) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.put('/api/profile/interests', {
        interest_ids: interestIds
      })
      profile.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '更新興趣標籤失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 上傳照片
   * @param {File} file - 圖片檔案
   */
  const uploadPhoto = async (file) => {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await apiClient.post('/api/profile/photos', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      // 重新取得完整檔案以更新照片列表
      await fetchProfile()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '上傳照片失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 刪除照片
   * @param {string} photoId - 照片 ID
   */
  const deletePhoto = async (photoId) => {
    loading.value = true
    error.value = null
    try {
      await apiClient.delete(`/api/profile/photos/${photoId}`)
      // 重新取得完整檔案以更新照片列表
      await fetchProfile()
    } catch (err) {
      error.value = err.response?.data?.detail || '刪除照片失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 取得所有興趣標籤
   * @param {string} category - 可選的分類篩選
   */
  const fetchInterestTags = async (category = null) => {
    loading.value = true
    error.value = null
    try {
      const params = category ? { category } : {}
      const response = await apiClient.get('/api/profile/interest-tags', { params })
      interestTags.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '無法取得興趣標籤'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 依分類分組興趣標籤
   */
  const getTagsByCategory = computed(() => {
    const grouped = {}
    interestTags.value.forEach(tag => {
      if (!grouped[tag.category]) {
        grouped[tag.category] = []
      }
      grouped[tag.category].push(tag)
    })
    return grouped
  })

  /**
   * 清除錯誤訊息
   */
  const clearError = () => {
    error.value = null
  }

  /**
   * 重置 Store
   */
  const $reset = () => {
    profile.value = null
    interestTags.value = []
    loading.value = false
    error.value = null
  }

  return {
    // State
    profile,
    interestTags,
    loading,
    error,

    // Getters
    hasProfile,
    isProfileComplete,
    profilePhotos,
    profileInterests,
    profilePicture,
    getTagsByCategory,

    // Actions
    fetchProfile,
    createProfile,
    updateProfile,
    updateInterests,
    uploadPhoto,
    deletePhoto,
    fetchInterestTags,
    clearError,
    $reset
  }
})
