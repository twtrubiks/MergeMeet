/**
 * useFormDirty Composable
 * 追蹤表單髒狀態並防止用戶意外遺失未儲存的資料
 *
 * 功能：
 * - 比對當前表單資料與原始資料
 * - 頁面離開前顯示確認對話框
 * - 關閉瀏覽器前顯示警告
 *
 * 使用方式:
 * ```js
 * const formData = ref({ name: '', email: '' })
 * const originalData = ref({ name: '', email: '' })
 *
 * const { isDirty, reset, setClean } = useFormDirty(formData, originalData)
 *
 * // 儲存成功後標記為乾淨
 * const handleSave = async () => {
 *   await saveData()
 *   setClean()
 * }
 * ```
 */

import { computed, watch, onMounted, onUnmounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

/**
 * 深度比較兩個值是否相等
 *
 * 限制：
 * - 不支援 Date、RegExp、Map、Set 等特殊類型
 * - 陣列會作為對象比較（索引作為鍵）
 * - 不處理循環引用
 *
 * 適用於：經過 JSON 序列化後的表單資料
 *
 * @param {*} a - 第一個要比較的值
 * @param {*} b - 第二個要比較的值
 * @returns {boolean} - 兩個值是否相等
 */
const deepEqual = (a, b) => {
  if (a === b) return true
  if (a == null || b == null) return false
  if (typeof a !== typeof b) return false

  if (typeof a === 'object') {
    const keysA = Object.keys(a)
    const keysB = Object.keys(b)

    if (keysA.length !== keysB.length) return false

    for (const key of keysA) {
      if (!keysB.includes(key)) return false
      if (!deepEqual(a[key], b[key])) return false
    }

    return true
  }

  return false
}

/**
 * 表單髒狀態追蹤 Composable
 *
 * @param {Ref} formData - 當前表單資料的 ref
 * @param {Ref} originalData - 原始表單資料的 ref
 * @param {Object} options - 選項
 * @param {boolean} options.confirmOnLeave - 是否在離開頁面前確認 (預設: true)
 * @param {string} options.confirmMessage - 確認訊息 (預設: '您有未儲存的變更，確定要離開嗎？')
 * @param {boolean} options.warnOnClose - 是否在關閉瀏覽器前警告 (預設: true)
 * @returns {Object} - { isDirty, reset, setClean }
 */
export function useFormDirty(formData, originalData, options = {}) {
  const {
    confirmOnLeave = true,
    confirmMessage = '您有未儲存的變更，確定要離開嗎？',
    warnOnClose = true
  } = options

  // 內部追蹤原始資料的副本
  const originalSnapshot = ref(null)

  // 是否為髒狀態
  const isDirty = computed(() => {
    if (!originalSnapshot.value) return false
    return !deepEqual(formData.value, originalSnapshot.value)
  })

  /**
   * 設定原始資料快照
   */
  const setSnapshot = () => {
    originalSnapshot.value = JSON.parse(JSON.stringify(originalData?.value || formData.value))
  }

  /**
   * 重置表單資料為原始值
   */
  const reset = () => {
    if (originalSnapshot.value) {
      Object.assign(formData.value, JSON.parse(JSON.stringify(originalSnapshot.value)))
    }
  }

  /**
   * 標記當前狀態為乾淨（通常在儲存成功後調用）
   */
  const setClean = () => {
    setSnapshot()
  }

  /**
   * 處理瀏覽器關閉/重新整理事件
   */
  const handleBeforeUnload = (event) => {
    if (isDirty.value && warnOnClose) {
      event.preventDefault()
      // 標準方式設定警告訊息（部分瀏覽器會忽略自訂訊息）
      event.returnValue = confirmMessage
      return confirmMessage
    }
  }

  // 監聽原始資料變化，更新快照
  watch(
    () => originalData?.value,
    () => {
      if (originalData?.value) {
        setSnapshot()
      }
    },
    { immediate: true, deep: true }
  )

  // 初始化時設定快照
  onMounted(() => {
    if (!originalSnapshot.value) {
      setSnapshot()
    }

    // 添加瀏覽器關閉警告
    if (warnOnClose) {
      window.addEventListener('beforeunload', handleBeforeUnload)
    }
  })

  // 清理事件監聽器
  onUnmounted(() => {
    window.removeEventListener('beforeunload', handleBeforeUnload)
  })

  // Vue Router 導航守衛
  if (confirmOnLeave) {
    onBeforeRouteLeave((to, from, next) => {
      if (isDirty.value) {
        const answer = window.confirm(confirmMessage)
        if (!answer) {
          return next(false)
        }
      }
      next()
    })
  }

  return {
    /**
     * 是否有未儲存的變更
     */
    isDirty,

    /**
     * 重置表單為原始值
     */
    reset,

    /**
     * 標記當前狀態為乾淨
     */
    setClean
  }
}
