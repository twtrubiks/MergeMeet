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
  const expandSuggestions = ref([]) // 空池時的偏好放寬建議
  const suggestionsLoading = ref(false)
  const likesYou = ref([]) // 誰喜歡我列表
  const likesYouLoading = ref(false)
  const lastPassedCandidate = ref(null) // 本 session 最後一次從卡堆跳過的候選人（供 Rewind）

  // Getters
  const hasCandidates = computed(() => candidates.value.length > 0)
  const hasMatches = computed(() => matches.value.length > 0)
  const matchCount = computed(() => matches.value.length)
  const hasLikesYou = computed(() => likesYou.value.length > 0)
  const canRewind = computed(() => lastPassedCandidate.value !== null)

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
   * 取得空池時的偏好放寬建議
   * 建議屬加值功能：失敗時回傳空陣列、不拋錯，空池畫面仍可正常顯示
   * @returns {Promise<Array>} 建議列表（type: 'distance' | 'age'）
   */
  const fetchExpandSuggestions = async () => {
    suggestionsLoading.value = true
    try {
      const response = await apiClient.get('/discovery/expand-suggestions')
      expandSuggestions.value = response.data?.suggestions || []
    } catch {
      expandSuggestions.value = []
    } finally {
      suggestionsLoading.value = false
    }
    return expandSuggestions.value
  }

  /**
   * 套用一則放寬建議：真的更新用戶偏好（PATCH /profile），再重新載入候選人
   * @param {Object} suggestion - fetchExpandSuggestions 回傳的其中一則
   */
  const applyExpandSuggestion = async (suggestion) => {
    const patch =
      suggestion.type === 'distance'
        ? { max_distance_km: suggestion.suggested_max_distance_km }
        : {
            min_age_preference: suggestion.suggested_min_age,
            max_age_preference: suggestion.suggested_max_age
          }

    error.value = null
    try {
      await apiClient.patch('/profile', patch)
    } catch (err) {
      error.value = err.response?.data?.detail || '更新偏好失敗'
      throw err
    }

    expandSuggestions.value = []
    return browseCandidates()
  }

  /**
   * 喜歡某個用戶
   * @param {string} userId - 用戶 ID
   * @param {Object|null} sourceCard - 發起喜歡的卡片資料（誰喜歡我頁傳入；
   *   探索卡堆不用傳，預設取 currentCandidate），配對成功時用於彈窗顯示
   * @returns {Object} { liked, is_match, match_id? }（對齊後端 LikeResponse）
   */
  const likeUser = async (userId, sourceCard = null) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(`/discovery/like/${userId}`)
      const result = response.data

      // 如果配對成功，保存配對用戶資訊用於顯示彈窗
      if (result.is_match) {
        lastMatchedUser.value = sourceCard || currentCandidate.value
        // 重新取得配對列表
        await fetchMatches()
      }

      // 候選人移除改由呼叫端在退場動畫結束後呼叫 removeCurrentCandidate()
      return result
    } catch (err) {
      const detail = err.response?.data?.detail
      if (err.response?.status === 429 && typeof detail === 'object') {
        error.value = detail.message || '今日喜歡次數已達上限'
      } else {
        error.value = typeof detail === 'string' ? detail : '操作失敗'
      }
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

      // 從卡堆跳過時記住這張卡，供 Rewind 撤銷（誰喜歡我頁的跳過不進卡堆，不記）
      if (currentCandidate.value?.user_id === userId) {
        lastPassedCandidate.value = currentCandidate.value
      }

      // 候選人移除改由呼叫端在退場動畫結束後呼叫 removeCurrentCandidate()
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || '操作失敗'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 撤銷上一次跳過（Rewind）
   * 刪除後端跳過記錄並把該候選人放回卡堆頂端。
   * 後端回 404（記錄已被清理）視同成功——對方本來就不再被排除。
   * @returns {Object|null} 被撤銷的候選人卡片，無可撤銷時回 null
   */
  const rewindLastPass = async () => {
    const card = lastPassedCandidate.value
    if (!card) return null

    error.value = null
    try {
      await apiClient.delete(`/discovery/pass/${card.user_id}`)
    } catch (err) {
      if (err.response?.status !== 404) {
        error.value = err.response?.data?.detail || '撤銷失敗'
        throw err
      }
    }

    // 放回卡堆頂端
    candidates.value.unshift(card)
    currentCandidate.value = card
    lastPassedCandidate.value = null
    return card
  }

  /**
   * 取得誰喜歡我列表
   * 從這頁按喜歡必定觸發配對（對方已喜歡我）
   */
  const fetchLikesYou = async () => {
    likesYouLoading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/discovery/likes-you')
      likesYou.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || '無法取得誰喜歡我列表'
      throw err
    } finally {
      likesYouLoading.value = false
    }
  }

  /**
   * 從誰喜歡我列表移除指定用戶（回喜歡或跳過後呼叫）
   * @param {string} userId - 用戶 ID
   */
  const removeFromLikesYou = (userId) => {
    likesYou.value = likesYou.value.filter((card) => card.user_id !== userId)
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
      matches.value = matches.value.filter((m) => m.match_id !== matchId)

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
    expandSuggestions.value = []
    suggestionsLoading.value = false
    likesYou.value = []
    likesYouLoading.value = false
    lastPassedCandidate.value = null
  }

  return {
    // State
    candidates,
    matches,
    currentCandidate,
    loading,
    error,
    lastMatchedUser,
    expandSuggestions,
    suggestionsLoading,
    likesYou,
    likesYouLoading,
    lastPassedCandidate,

    // Getters
    hasCandidates,
    hasMatches,
    matchCount,
    hasLikesYou,
    canRewind,

    // Actions
    browseCandidates,
    fetchExpandSuggestions,
    applyExpandSuggestion,
    likeUser,
    passUser,
    rewindLastPass,
    fetchLikesYou,
    removeFromLikesYou,
    fetchMatches,
    unmatch,
    removeCurrentCandidate,
    clearLastMatch,
    clearError,
    $reset
  }
})
