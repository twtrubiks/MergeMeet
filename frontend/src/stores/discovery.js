/**
 * Discovery Store
 * 管理探索與配對相關狀態和 API 呼叫
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api/client'

export const useDiscoveryStore = defineStore('discovery', () => {
  // State
  const candidates = ref([])
  const matches = ref([])
  const currentCandidate = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const lastMatchedUser = ref(null) // 用於顯示配對成功彈窗

  // Getters
  const hasCandidates = computed(() => candidates.value.length > 0)
  const hasMatches = computed(() => matches.value.length > 0)
  const matchCount = computed(() => matches.value.length)

  /**
   * 瀏覽候選人列表
   * @param {number} limit - 限制數量 (預設 20)
   */
  const browseCandidates = async (limit = 20) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/discovery/browse', {
        params: { limit }
      })
      candidates.value = response.data

      // 設置當前候選人為第一個
      if (candidates.value.length > 0) {
        currentCandidate.value = candidates.value[0]
      } else {
        currentCandidate.value = null
      }

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '無法取得候選人列表'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 喜歡某個用戶
   * @param {string} userId - 用戶 ID
   * @returns {Object} { liked, matched, match_id? }
   */
  const likeUser = async (userId) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(`/discovery/like/${userId}`)
      const result = response.data

      // 如果配對成功，保存配對用戶資訊用於顯示彈窗
      if (result.matched) {
        lastMatchedUser.value = currentCandidate.value
        // 重新取得配對列表
        await fetchMatches()
      }

      // 移除當前候選人
      removeCurrentCandidate()

      return result
    } catch (err) {
      error.value = err.response?.data?.detail || '操作失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 跳過某個用戶
   * @param {string} userId - 用戶 ID
   */
  const passUser = async (userId) => {
    loading.value = true
    error.value = null
    try {
      await apiClient.post(`/discovery/pass/${userId}`)

      // 移除當前候選人
      removeCurrentCandidate()

      return true
    } catch (err) {
      error.value = err.response?.data?.detail || '操作失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 取得配對列表
   */
  const fetchMatches = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/discovery/matches')
      matches.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '無法取得配對列表'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 取消配對
   * @param {string} matchId - 配對 ID
   */
  const unmatch = async (matchId) => {
    loading.value = true
    error.value = null
    try {
      await apiClient.delete(`/discovery/unmatch/${matchId}`)

      // 從列表中移除
      matches.value = matches.value.filter(m => m.match_id !== matchId)

      return true
    } catch (err) {
      error.value = err.response?.data?.detail || '取消配對失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 移除當前候選人並切換到下一個
   */
  const removeCurrentCandidate = () => {
    if (candidates.value.length > 0) {
      candidates.value.shift()
      currentCandidate.value = candidates.value[0] || null
    }
  }

  /**
   * 清除上次配對成功的用戶（關閉彈窗後調用）
   */
  const clearLastMatch = () => {
    lastMatchedUser.value = null
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
    candidates.value = []
    matches.value = []
    currentCandidate.value = null
    loading.value = false
    error.value = null
    lastMatchedUser.value = null
  }

  return {
    // State
    candidates,
    matches,
    currentCandidate,
    loading,
    error,
    lastMatchedUser,

    // Getters
    hasCandidates,
    hasMatches,
    matchCount,

    // Actions
    browseCandidates,
    likeUser,
    passUser,
    fetchMatches,
    unmatch,
    removeCurrentCandidate,
    clearLastMatch,
    clearError,
    $reset
  }
})
