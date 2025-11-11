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
      >
        <img :src="photo.url" :alt="'Photo ' + photo.display_order" />
        <div class="photo-overlay">
          <button @click="handleDelete(photo.id)" class="btn-delete" title="刪除">
            🗑️
          </button>
          <div v-if="photo.is_profile_picture" class="photo-badge">主頭像</div>
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
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useProfileStore } from '@/stores/profile'

const emit = defineEmits(['photos-changed'])

const profileStore = useProfileStore()
const fileInput = ref(null)
const uploading = ref(false)
const error = ref(null)

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

  // 驗證檔案大小 (10MB)
  if (file.size > 10 * 1024 * 1024) {
    error.value = '圖片大小不能超過 10MB'
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

@media (max-width: 768px) {
  .photo-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
