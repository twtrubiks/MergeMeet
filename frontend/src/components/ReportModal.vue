<template>
  <Transition name="modal">
    <div v-if="show" class="modal-overlay" @click="handleClose">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>舉報用戶</h2>
          <button class="close-btn" @click="handleClose">✕</button>
        </div>

        <div class="modal-body">
          <p class="warning-text">請提供詳細的舉報理由，協助我們建立更安全的社群環境。</p>

          <!-- 舉報類型 -->
          <div class="form-group">
            <label for="report-type">舉報類型 *</label>
            <select
              id="report-type"
              v-model="reportType"
              class="form-control"
              :disabled="loading"
            >
              <option value="">請選擇舉報類型</option>
              <option value="INAPPROPRIATE">不當內容或行為</option>
              <option value="HARASSMENT">騷擾或霸凌</option>
              <option value="FAKE">假帳號或冒充</option>
              <option value="SCAM">詐騙或欺詐</option>
              <option value="OTHER">其他</option>
            </select>
          </div>

          <!-- 舉報原因 -->
          <div class="form-group">
            <label for="reason">詳細原因 * (至少 10 字)</label>
            <textarea
              id="reason"
              v-model="reason"
              class="form-control"
              rows="4"
              placeholder="請詳細描述舉報原因..."
              :disabled="loading"
              maxlength="1000"
            ></textarea>
            <div class="char-count">{{ reason.length }} / 1000</div>
          </div>

          <!-- 證據說明 (選填) -->
          <div class="form-group">
            <label for="evidence">證據說明 (選填)</label>
            <textarea
              id="evidence"
              v-model="evidence"
              class="form-control"
              rows="3"
              placeholder="如有相關證據或截圖，請說明..."
              :disabled="loading"
              maxlength="2000"
            ></textarea>
            <div class="char-count">{{ evidence.length }} / 2000</div>
          </div>

          <!-- 錯誤訊息 -->
          <div v-if="error" class="error-message">
            ❌ {{ error }}
          </div>

          <!-- 成功訊息 -->
          <div v-if="success" class="success-message">
            ✅ 舉報已送出，感謝您的協助！
          </div>
        </div>

        <div class="modal-footer">
          <button
            class="btn btn-cancel"
            @click="handleClose"
            :disabled="loading"
          >
            取消
          </button>
          <button
            class="btn btn-report"
            @click="handleSubmit"
            :disabled="!canSubmit || loading"
          >
            {{ loading ? '送出中...' : '送出舉報' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useSafetyStore } from '@/stores/safety'

const props = defineProps({
  show: {
    type: Boolean,
    required: true
  },
  reportedUser: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'reported'])

const safetyStore = useSafetyStore()

// 表單資料
const reportType = ref('')
const reason = ref('')
const evidence = ref('')
const loading = ref(false)
const error = ref(null)
const success = ref(false)

// 表單驗證
const canSubmit = computed(() => {
  return reportType.value &&
         reason.value.length >= 10 &&
         !loading.value &&
         !success.value
})

// 處理送出
const handleSubmit = async () => {
  if (!canSubmit.value || !props.reportedUser) return

  loading.value = true
  error.value = null

  try {
    await safetyStore.reportUser({
      reported_user_id: props.reportedUser.user_id,
      report_type: reportType.value,
      reason: reason.value,
      evidence: evidence.value || null
    })

    success.value = true
    emit('reported')

    // 2 秒後自動關閉
    setTimeout(() => {
      handleClose()
    }, 2000)
  } catch (err) {
    error.value = err.response?.data?.detail || '舉報失敗，請稍後再試'
  } finally {
    loading.value = false
  }
}

// 處理關閉
const handleClose = () => {
  if (loading.value) return
  emit('close')
}

// 重置表單
const resetForm = () => {
  reportType.value = ''
  reason.value = ''
  evidence.value = ''
  error.value = null
  success.value = false
}

// 監聽 show 變化，重置表單
watch(() => props.show, (newVal) => {
  if (newVal) {
    resetForm()
  }
})
</script>

<style scoped>
/* Modal 遮罩 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

/* Modal 內容 */
.modal-content {
  background: white;
  border-radius: 20px;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

/* Modal 標題 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #333;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #f5f5f5;
  color: #666;
}

/* Modal 內容區 */
.modal-body {
  padding: 24px;
}

.warning-text {
  font-size: 14px;
  color: #666;
  margin-bottom: 20px;
  padding: 12px;
  background: #FFF3E0;
  border-left: 3px solid #FF9800;
  border-radius: 4px;
}

/* 表單群組 */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.form-control {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  transition: border-color 0.2s ease;
}

.form-control:focus {
  outline: none;
  border-color: #FF6B6B;
}

.form-control:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

select.form-control {
  cursor: pointer;
}

textarea.form-control {
  resize: vertical;
  min-height: 100px;
}

.char-count {
  text-align: right;
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

/* 訊息 */
.error-message,
.success-message {
  padding: 12px;
  border-radius: 8px;
  margin-top: 16px;
  font-size: 14px;
}

.error-message {
  background: #FFEBEE;
  color: #C62828;
  border-left: 3px solid #C62828;
}

.success-message {
  background: #E8F5E9;
  color: #2E7D32;
  border-left: 3px solid #2E7D32;
}

/* Modal 底部 */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 24px;
  border-top: 1px solid #f0f0f0;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  background: #f5f5f5;
  color: #666;
}

.btn-cancel:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-report {
  background: #FF6B6B;
  color: white;
}

.btn-report:hover:not(:disabled) {
  background: #FF5252;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
}

/* 動畫 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .modal-content,
.modal-leave-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.9);
}

/* 響應式設計 */
@media (max-width: 768px) {
  .modal-content {
    max-height: 95vh;
  }

  .modal-header h2 {
    font-size: 20px;
  }

  .modal-body {
    padding: 20px 16px;
  }

  .modal-footer {
    padding: 12px 16px 20px;
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>
