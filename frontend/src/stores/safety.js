/**
 * Safety Store
 * 管理封鎖和舉報相關狀態和 API 呼叫
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api/client'

export const useSafetyStore = defineStore('safety', () => {
  // State
  const blockedUsers = ref([])
  const myReports = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const hasBlockedUsers = computed(() => blockedUsers.value.length > 0)
  const blockedUserIds = computed(() =>
    blockedUsers.value.map(u => u.blocked_user_id)
  )

  /**
   * 封鎖用戶
   * @param {string} userId - 用戶 ID
   * @param {string} reason - 封鎖原因
   */
  const blockUser = async (userId, reason = null) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(`/safety/block/${userId}`, {
        reason
      })

      // 重新載入封鎖列表
      await fetchBlockedUsers()

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '封鎖失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 解除封鎖用戶
   * @param {string} userId - 用戶 ID
   */
  const unblockUser = async (userId) => {
    loading.value = true
    error.value = null
    try {
      await apiClient.delete(`/safety/block/${userId}`)

      // 從列表中移除
      blockedUsers.value = blockedUsers.value.filter(
        u => u.blocked_user_id !== userId
      )

      return true
    } catch (err) {
      error.value = err.response?.data?.detail || '解除封鎖失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 取得封鎖列表
   */
  const fetchBlockedUsers = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/safety/blocked')
      blockedUsers.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '無法取得封鎖列表'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 檢查用戶是否已被封鎖
   * @param {string} userId - 用戶 ID
   */
  const isBlocked = (userId) => {
    return blockedUserIds.value.includes(userId)
  }

  /**
   * 舉報用戶
   * @param {Object} reportData - 舉報資料
   */
  const reportUser = async (reportData) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post('/safety/report', reportData)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '舉報失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 取得我的舉報記錄
   */
  const fetchMyReports = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/safety/reports')
      myReports.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '無法取得舉報記錄'
      throw err
    } finally {
      loading.value = false
    }
  }

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
    blockedUsers.value = []
    myReports.value = []
    loading.value = false
    error.value = null
  }

  return {
    // State
    blockedUsers,
    myReports,
    loading,
    error,

    // Getters
    hasBlockedUsers,
    blockedUserIds,

    // Actions
    blockUser,
    unblockUser,
    fetchBlockedUsers,
    isBlocked,
    reportUser,
    fetchMyReports,
    clearError,
    $reset
  }
})
