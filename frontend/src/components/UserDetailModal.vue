<template>
  <Transition name="modal">
    <div v-if="show" class="modal-overlay" @click="handleClose">
      <div class="modal-container" @click.stop>
        <!-- 關閉按鈕 -->
        <button class="close-btn" @click="handleClose" aria-label="關閉">
          <span>×</span>
        </button>

        <!-- 照片輪播區 -->
        <div class="photo-carousel">
          <div
            v-if="photos.length > 0"
            class="carousel-track"
            :style="{ transform: `translateX(-${currentPhotoIndex * 100}%)` }"
          >
            <div
              v-for="(photo, index) in photos"
              :key="index"
              class="carousel-slide"
            >
              <img :src="photo" :alt="`${user.display_name} 的照片 ${index + 1}`" />
            </div>
          </div>

          <!-- 無照片時的 placeholder -->
          <div v-else class="photo-placeholder">
            <span class="placeholder-text">{{ user.display_name?.[0] || '?' }}</span>
          </div>

          <!-- 左右切換按鈕 -->
          <template v-if="photos.length > 1">
            <button class="carousel-btn prev" @click.stop="prevPhoto" aria-label="上一張">
              ‹
            </button>
            <button class="carousel-btn next" @click.stop="nextPhoto" aria-label="下一張">
              ›
            </button>
          </template>

          <!-- 指示器 -->
          <div v-if="photos.length > 1" class="carousel-indicators">
            <span
              v-for="(_, index) in photos"
              :key="index"
              class="indicator"
              :class="{ active: index === currentPhotoIndex }"
              @click.stop="goToPhoto(index)"
            ></span>
          </div>
        </div>

        <!-- 用戶資訊 -->
        <div class="user-details">
          <!-- 名字和年齡 -->
          <div class="user-header">
            <h2 class="user-name">{{ user.display_name }}</h2>
            <span class="user-age">{{ user.age }}</span>
          </div>

          <!-- 距離 -->
          <p v-if="user.distance_km !== null && user.distance_km !== undefined" class="user-distance">
            <span class="distance-icon">📍</span>
            {{ formatDistance(user.distance_km) }}
          </p>

          <!-- 興趣標籤 -->
          <div v-if="user.interests && user.interests.length > 0" class="user-interests">
            <span
              v-for="interest in user.interests"
              :key="interest"
              class="interest-tag"
            >
              {{ interest }}
            </span>
          </div>

          <!-- 自我介紹 -->
          <div v-if="user.bio" class="user-bio">
            <h3 class="bio-title">關於我</h3>
            <p class="bio-content">{{ user.bio }}</p>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    required: true
  },
  user: {
    type: Object,
    required: true,
    default: () => ({})
  }
})

const emit = defineEmits(['close'])

// 照片輪播狀態
const currentPhotoIndex = ref(0)

// 計算照片列表
const photos = computed(() => {
  if (!props.user) return []
  // 支援 photos 陣列或單一 profile_picture
  if (Array.isArray(props.user.photos) && props.user.photos.length > 0) {
    return props.user.photos
  }
  if (props.user.profile_picture) {
    return [props.user.profile_picture]
  }
  return []
})

// 照片切換
const prevPhoto = () => {
  if (currentPhotoIndex.value > 0) {
    currentPhotoIndex.value--
  } else {
    currentPhotoIndex.value = photos.value.length - 1
  }
}

const nextPhoto = () => {
  if (currentPhotoIndex.value < photos.value.length - 1) {
    currentPhotoIndex.value++
  } else {
    currentPhotoIndex.value = 0
  }
}

const goToPhoto = (index) => {
  currentPhotoIndex.value = index
}

// 距離格式化
const formatDistance = (km) => {
  if (km === null || km === undefined) return ''
  if (km < 1) return `${Math.round(km * 1000)}m`
  if (km < 10) return `${km.toFixed(1)}km`
  return `${Math.round(km)}km`
}

// 關閉 Modal
const handleClose = () => {
  emit('close')
}

// ESC 鍵關閉
const handleKeydown = (event) => {
  if (event.key === 'Escape' && props.show) {
    handleClose()
  }
}

// 監聽 show 狀態
watch(() => props.show, (newVal) => {
  if (newVal) {
    // 開啟時重置照片索引並添加鍵盤監聽
    currentPhotoIndex.value = 0
    window.addEventListener('keydown', handleKeydown)
    // 防止背景滾動
    document.body.style.overflow = 'hidden'
  } else {
    window.removeEventListener('keydown', handleKeydown)
    document.body.style.overflow = ''
  }
})

// 組件卸載時清理
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* Modal 覆蓋層 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

/* Modal 容器 */
.modal-container {
  background: white;
  border-radius: 20px;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
  position: relative;
  display: flex;
  flex-direction: column;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* 關閉按鈕 */
.close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  font-size: 24px;
  cursor: pointer;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.7);
}

/* 照片輪播區 */
.photo-carousel {
  position: relative;
  width: 100%;
  height: 400px;
  overflow: hidden;
  flex-shrink: 0;
}

.carousel-track {
  display: flex;
  height: 100%;
  transition: transform 0.3s ease;
}

.carousel-slide {
  flex: 0 0 100%;
  width: 100%;
  height: 100%;
}

.carousel-slide img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 無照片 placeholder */
.photo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
}

.placeholder-text {
  font-size: 120px;
  font-weight: bold;
  color: white;
  text-transform: uppercase;
}

/* 切換按鈕 */
.carousel-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  font-size: 28px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.carousel-btn:hover {
  background: white;
  transform: translateY(-50%) scale(1.1);
}

.carousel-btn.prev {
  left: 12px;
}

.carousel-btn.next {
  right: 12px;
}

/* 指示器 */
.carousel-indicators {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
}

.indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s;
}

.indicator.active {
  background: white;
  transform: scale(1.3);
}

.indicator:hover:not(.active) {
  background: rgba(255, 255, 255, 0.8);
}

/* 用戶資訊區 */
.user-details {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

/* 名字和年齡 */
.user-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 8px;
}

.user-name {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  margin: 0;
}

.user-age {
  font-size: 24px;
  font-weight: 400;
  color: #666;
}

/* 距離 */
.user-distance {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
  color: #888;
  margin: 0 0 16px;
}

.distance-icon {
  font-size: 14px;
}

/* 興趣標籤 */
.user-interests {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}

.interest-tag {
  display: inline-block;
  padding: 8px 16px;
  background: #FFF0F0;
  color: #FF6B6B;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

/* 自我介紹 */
.user-bio {
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.bio-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0 0 8px;
}

.bio-content {
  font-size: 15px;
  line-height: 1.6;
  color: #555;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
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

/* 響應式設計 */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 10px;
  }

  .photo-carousel {
    height: 350px;
  }

  .user-details {
    padding: 20px;
  }

  .user-name {
    font-size: 24px;
  }

  .user-age {
    font-size: 20px;
  }

  .placeholder-text {
    font-size: 80px;
  }
}

@media (max-width: 480px) {
  .photo-carousel {
    height: 300px;
  }

  .carousel-btn {
    width: 36px;
    height: 36px;
    font-size: 24px;
  }

  .user-details {
    padding: 16px;
  }

  .user-name {
    font-size: 22px;
  }

  .user-age {
    font-size: 18px;
  }

  .interest-tag {
    padding: 6px 12px;
    font-size: 13px;
  }
}
</style>
