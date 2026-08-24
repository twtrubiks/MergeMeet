<template>
  <Transition name="modal">
    <div
      v-if="show"
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="用戶詳情"
      @click="handleClose"
    >
      <div class="modal-container" @click.stop>
        <!-- 關閉按鈕 -->
        <button class="close-btn" aria-label="關閉" @click="handleClose">
          <span>×</span>
        </button>

        <!-- 照片輪播區 -->
        <div class="photo-carousel">
          <div
            v-if="photos.length > 0"
            class="carousel-track"
            :style="{ transform: `translateX(-${currentPhotoIndex * 100}%)` }"
          >
            <div v-for="(photo, index) in photos" :key="index" class="carousel-slide">
              <img :src="photo" :alt="`${user.display_name} 的照片 ${index + 1}`" />
            </div>
          </div>

          <!-- 無照片時的 placeholder -->
          <div v-else class="photo-placeholder">
            <span class="placeholder-text">{{ user.display_name?.[0] || '?' }}</span>
          </div>

          <!-- 左右切換按鈕 -->
          <template v-if="photos.length > 1">
            <button class="carousel-btn prev" aria-label="上一張" @click.stop="prevPhoto">‹</button>
            <button class="carousel-btn next" aria-label="下一張" @click.stop="nextPhoto">›</button>
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
          <p
            v-if="user.distance_km !== null && user.distance_km !== undefined"
            class="user-distance"
          >
            <Icon name="location" size="sm" decorative />
            {{ formatDistance(user.distance_km) }}
          </p>

          <!-- 共同興趣（配對理由） -->
          <div v-if="commonInterests.length > 0" class="common-interests">
            <h3 class="section-title">
              <Icon name="heart" size="sm" decorative class="section-icon" />
              你們都喜歡
            </h3>
            <div class="user-interests">
              <span
                v-for="interest in commonInterests"
                :key="interest"
                class="interest-tag interest-tag--common"
              >
                {{ interest }}
              </span>
            </div>
          </div>

          <!-- 其他興趣標籤（排除已列在共同興趣的） -->
          <div v-if="otherInterests.length > 0" class="other-interests">
            <h3 v-if="commonInterests.length > 0" class="section-title">其他興趣</h3>
            <div class="user-interests">
              <span v-for="interest in otherInterests" :key="interest" class="interest-tag">
                {{ interest }}
              </span>
            </div>
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
import Icon from '@/components/ui/Icon.vue'
import { formatDistance } from '@/utils/distance'

const props = defineProps({
  show: {
    type: Boolean,
    required: true
  },
  user: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close'])

// 照片輪播狀態
const currentPhotoIndex = ref(0)

// 計算照片列表
const photos = computed(() => {
  return Array.isArray(props.user?.photos) ? props.user.photos : []
})

// 共同興趣（配對理由），依候選人興趣順序
const commonInterests = computed(() => props.user?.common_interests || [])

// 其餘興趣（排除已列在共同興趣的，避免重複顯示）
const otherInterests = computed(() => {
  const common = new Set(commonInterests.value)
  return (props.user?.interests || []).filter((i) => !common.has(i))
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
watch(
  () => props.show,
  (newVal) => {
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
  }
)

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
  border-radius: var(--radius-xl);
  max-width: min(500px, calc(100vw - 40px));
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
  min-width: 44px;
  min-height: 44px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  font-size: var(--font-size-2xl);
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

.close-btn:focus-visible {
  outline: 3px solid white;
  outline-offset: 2px;
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
  background: linear-gradient(135deg, #ff6b6b, #ff8e53);
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
  color: var(--color-text-primary);
  font-size: var(--font-size-3xl);
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

.carousel-btn:focus-visible {
  outline: 3px solid var(--color-primary-600);
  outline-offset: 2px;
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
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.user-age {
  font-size: var(--font-size-2xl);
  font-weight: 400;
  color: var(--color-text-muted);
}

/* 距離 */
.user-distance {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-base);
  color: var(--color-text-light);
  margin: 0 0 16px;
}

.distance-icon {
  font-size: var(--font-size-sm);
}

/* 興趣標籤 */
.user-interests {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 8px;
}

.section-icon {
  color: var(--color-primary-600);
}

.interest-tag {
  display: inline-block;
  padding: 8px 16px;
  background: #fff0f0;
  color: var(--color-like-accessible);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

/* 共同興趣：實色主色底 + 白字（對比 ≈ 4.9:1，符合 WCAG AA 小字） */
.interest-tag--common {
  background: var(--color-primary-600);
  color: #fff;
  font-weight: 600;
}

/* 自我介紹 */
.user-bio {
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}

.bio-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 8px;
}

.bio-content {
  font-size: var(--font-size-base);
  line-height: 1.6;
  color: var(--color-text-secondary);
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

  /* Keep touch targets at 44px minimum */
  .carousel-btn {
    min-width: 44px;
    min-height: 44px;
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
