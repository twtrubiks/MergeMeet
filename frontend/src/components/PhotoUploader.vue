<template>
  <div class="photo-uploader">
    <h3>照片 ({{ profileStore.profilePhotos.length }}/6)</h3>
    <p class="hint">上傳最多 6 張照片，第一張將作為主頭像</p>

    <!-- 照片網格 -->
    <div class="photo-grid">
      <!-- 現有照片 -->
      <div
        v-for="photo in profileStore.profilePhotos"
        :key="photo.id"
        class="photo-card"
        :class="{
          'photo-pending': photo.moderation_status === 'PENDING',
          'photo-rejected': photo.moderation_status === 'REJECTED'
        }"
      >
        <img :src="photo.url" :alt="'Photo ' + photo.display_order" />
        <div class="photo-overlay">
          <button @click="handleDelete(photo.id)" class="btn-delete" title="刪除">
            🗑️
          </button>
          <div v-if="photo.is_profile_picture" class="photo-badge">主頭像</div>
        </div>
        <!-- 審核狀態標籤 -->
        <div
          v-if="photo.moderation_status"
          class="moderation-badge"
          :class="getModerationStatusClass(photo.moderation_status)"
          :title="photo.moderation_status === 'REJECTED' ? photo.rejection_reason : ''"
        >
          {{ getModerationStatusText(photo.moderation_status) }}
        </div>
        <!-- 待審核遮罩 -->
        <div v-if="photo.moderation_status === 'PENDING'" class="pending-mask">
          <span>⏳ 審核中</span>
        </div>
        <!-- 被拒絕提示 -->
        <div v-if="photo.moderation_status === 'REJECTED'" class="rejected-mask">
          <span>❌ 未通過</span>
          <small v-if="photo.rejection_reason">{{ photo.rejection_reason }}</small>
          <button
            class="appeal-btn"
            @click.stop="openAppealModal(photo)"
          >
            提出申訴
          </button>
        </div>
      </div>

      <!-- 上傳按鈕 -->
      <div
        v-if="profileStore.profilePhotos.length < 6"
        class="photo-card upload-card"
        @click="triggerFileInput"
      >
        <div class="upload-icon">
          <span v-if="!uploading">📷</span>
          <div v-else class="spinner-small"></div>
        </div>
        <p>{{ uploading ? '上傳中...' : '新增照片' }}</p>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          @change="handleFileSelect"
          style="display: none"
        />
      </div>
    </div>

    <!-- 錯誤訊息 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- 申訴 Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showAppealModal" class="appeal-modal-overlay" @click="closeAppealModal">
          <div class="appeal-modal" @click.stop>
            <h3>照片申訴</h3>

            <!-- 照片預覽 -->
            <div class="appeal-photo-preview">
              <img :src="appealingPhoto?.url" alt="被拒絕的照片" />
            </div>

            <!-- 拒絕原因 -->
            <div class="appeal-reason-display">
              <label>拒絕原因：</label>
              <p>{{ appealingPhoto?.rejection_reason || '未說明' }}</p>
            </div>

            <!-- 申訴理由 -->
            <div class="appeal-form">
              <label for="appeal-reason">申訴理由：</label>
              <textarea
                id="appeal-reason"
                v-model="appealReason"
                placeholder="請詳細說明為什麼您認為這張照片應該通過審核（至少 20 字）"
                maxlength="1000"
                rows="4"
              ></textarea>
              <div class="char-count">{{ appealReason.length }}/1000</div>
            </div>

            <!-- 操作按鈕 -->
            <div class="appeal-actions">
              <button class="btn-cancel" @click="closeAppealModal">取消</button>
              <button
                class="btn-submit"
                @click="submitAppeal"
                :disabled="appealLoading || appealReason.length < 20"
              >
                {{ appealLoading ? '提交中...' : '提交申訴' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useProfileStore } from '@/stores/profile'
import apiClient from '@/api/client'
import { logger } from '@/utils/logger'

const emit = defineEmits(['photos-changed'])

const profileStore = useProfileStore()
const fileInput = ref(null)
const uploading = ref(false)
const error = ref(null)

// 申訴相關狀態
const showAppealModal = ref(false)
const appealingPhoto = ref(null)
const appealReason = ref('')
const appealLoading = ref(false)

/**
 * 觸發檔案選擇
 */
const triggerFileInput = () => {
  if (!uploading.value) {
    fileInput.value?.click()
  }
}

/**
 * 處理檔案選擇
 */
const handleFileSelect = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  // 驗證檔案類型
  if (!file.type.startsWith('image/')) {
    error.value = '只能上傳圖片檔案'
    return
  }

  // 驗證檔案大小 (5MB，與後端 MAX_UPLOAD_SIZE 一致)
  if (file.size > 5 * 1024 * 1024) {
    error.value = '圖片大小不能超過 5MB'
    return
  }

  // 上傳
  uploading.value = true
  error.value = null

  try {
    await profileStore.uploadPhoto(file)
    emit('photos-changed')
    // 清除檔案輸入
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  } catch (err) {
    error.value = err.response?.data?.detail || '上傳失敗'
  } finally {
    uploading.value = false
  }
}

/**
 * 取得審核狀態文字
 */
const getModerationStatusText = (status) => {
  const statusText = {
    PENDING: '審核中',
    APPROVED: '已通過',
    REJECTED: '未通過'
  }
  return statusText[status] || status
}

/**
 * 取得審核狀態樣式類別
 */
const getModerationStatusClass = (status) => {
  return {
    'status-pending': status === 'PENDING',
    'status-approved': status === 'APPROVED',
    'status-rejected': status === 'REJECTED'
  }
}

/**
 * 處理刪除照片
 */
const handleDelete = async (photoId) => {
  if (!confirm('確定要刪除這張照片嗎？')) {
    return
  }

  error.value = null

  try {
    await profileStore.deletePhoto(photoId)
    emit('photos-changed')
  } catch (err) {
    error.value = err.response?.data?.detail || '刪除失敗'
  }
}

/**
 * 開啟申訴 Modal
 */
const openAppealModal = (photo) => {
  appealingPhoto.value = photo
  appealReason.value = ''
  showAppealModal.value = true
}

/**
 * 關閉申訴 Modal
 */
const closeAppealModal = () => {
  showAppealModal.value = false
  appealingPhoto.value = null
  appealReason.value = ''
}

/**
 * 提交申訴
 */
const submitAppeal = async () => {
  if (appealReason.value.length < 20) {
    error.value = '申訴理由至少需要 20 字'
    return
  }

  appealLoading.value = true
  error.value = null

  try {
    await apiClient.post('/moderation/appeals', {
      appeal_type: 'PHOTO',
      rejected_content: appealingPhoto.value.url,
      violations: appealingPhoto.value.rejection_reason || '未說明',
      reason: appealReason.value
    })

    logger.debug('[PhotoUploader] Appeal submitted successfully')
    alert('申訴已提交，請等待審核')
    closeAppealModal()
  } catch (err) {
    logger.error('[PhotoUploader] Appeal failed:', err)
    error.value = err.response?.data?.detail || '申訴提交失敗'
  } finally {
    appealLoading.value = false
  }
}
</script>

<style scoped>
.photo-uploader {
  margin: 1.5rem 0;
}

.photo-uploader h3 {
  margin-bottom: 0.5rem;
  color: #333;
}

.hint {
  color: #999;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
}

.photo-card {
  position: relative;
  aspect-ratio: 1;
  border-radius: 12px;
  overflow: hidden;
  background: #f5f5f5;
  cursor: pointer;
}

.photo-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s;
}

.photo-card:hover .photo-overlay {
  background: rgba(0, 0, 0, 0.5);
}

.btn-delete {
  background: white;
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  font-size: 1.2rem;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.3s, transform 0.2s;
}

.photo-card:hover .btn-delete {
  opacity: 1;
}

.btn-delete:hover {
  transform: scale(1.1);
}

.photo-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(102, 126, 234, 0.9);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.upload-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #ccc;
  background: #fafafa;
  transition: border-color 0.3s, background 0.3s;
}

.upload-card:hover {
  border-color: #667eea;
  background: #f0f0ff;
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.upload-card p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.spinner-small {
  width: 30px;
  height: 30px;
  border: 3px solid #e0e0e0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  margin-top: 1rem;
  padding: 12px;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c33;
  font-size: 0.9rem;
}

/* 審核狀態相關樣式 */
.photo-pending {
  opacity: 0.7;
}

.photo-rejected {
  border: 2px solid #ff4d4f;
}

.moderation-badge {
  position: absolute;
  bottom: 8px;
  left: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  color: white;
  z-index: 10;
}

.moderation-badge.status-pending {
  background: rgba(250, 173, 20, 0.9);
}

.moderation-badge.status-approved {
  background: rgba(82, 196, 26, 0.9);
}

.moderation-badge.status-rejected {
  background: rgba(255, 77, 79, 0.9);
}

.pending-mask {
  position: absolute;
  inset: 0;
  background: rgba(250, 173, 20, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.pending-mask span {
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
}

.rejected-mask {
  position: absolute;
  inset: 0;
  background: rgba(255, 77, 79, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  gap: 4px;
}

.rejected-mask span {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
}

.rejected-mask small {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  max-width: 80%;
  text-align: center;
  word-break: break-word;
}

@media (max-width: 768px) {
  .photo-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 申訴按鈕 */
.appeal-btn {
  margin-top: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.9);
  color: #ff6b6b;
  border: 1px solid #ff6b6b;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.2s;
}

.appeal-btn:hover {
  background: #ff6b6b;
  color: white;
}

/* 申訴 Modal */
.appeal-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.appeal-modal {
  background: white;
  border-radius: 16px;
  max-width: 450px;
  width: 100%;
  padding: 24px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.appeal-modal h3 {
  margin: 0 0 20px;
  font-size: 1.25rem;
  color: #333;
  text-align: center;
}

.appeal-photo-preview {
  width: 100%;
  height: 200px;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}

.appeal-photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.appeal-reason-display {
  margin-bottom: 16px;
}

.appeal-reason-display label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}

.appeal-reason-display p {
  margin: 0;
  padding: 10px;
  background: #fff5f5;
  border-radius: 6px;
  color: #c33;
  font-size: 0.9rem;
}

.appeal-form {
  margin-bottom: 20px;
}

.appeal-form label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
}

.appeal-form textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 0.9rem;
  resize: vertical;
  font-family: inherit;
}

.appeal-form textarea:focus {
  outline: none;
  border-color: #ff6b6b;
}

.char-count {
  text-align: right;
  font-size: 0.75rem;
  color: #999;
  margin-top: 4px;
}

.appeal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 10px 20px;
  background: #f5f5f5;
  color: #666;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-cancel:hover {
  background: #e0e0e0;
}

.btn-submit {
  padding: 10px 20px;
  background: #ff6b6b;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-submit:hover:not(:disabled) {
  background: #ff5252;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal 過渡效果 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .appeal-modal,
.modal-leave-active .appeal-modal {
  transition: transform 0.3s ease;
}

.modal-enter-from .appeal-modal,
.modal-leave-to .appeal-modal {
  transform: translateY(-20px);
}
</style>
