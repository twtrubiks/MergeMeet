<template>
  <Transition name="modal">
    <div v-if="show" class="modal-overlay" @click="handleClose">
      <div class="modal-container" @click.stop>
        <div class="modal-content">
          <!-- 配對成功圖示 -->
          <div class="match-icon">
            <div class="heart-animation">
              💕
            </div>
          </div>

          <!-- 標題 -->
          <h2 class="modal-title">配對成功！</h2>
          <p class="modal-subtitle">你們互相喜歡對方</p>

          <!-- 用戶資訊 -->
          <div v-if="matchedUser" class="user-info">
            <div class="user-avatar">
              <img
                v-if="matchedUser.photos?.length"
                :src="matchedUser.photos[0]"
                :alt="matchedUser.display_name"
              >
              <div v-else class="avatar-placeholder">
                {{ matchedUser.display_name[0] }}
              </div>
            </div>
            <h3 class="user-name">{{ matchedUser.display_name }}</h3>
            <p class="user-age">{{ matchedUser.age }} 歲</p>

            <!-- 共同興趣 -->
            <div v-if="matchedUser.interests && matchedUser.interests.length > 0" class="common-interests">
              <p class="interests-title">共同興趣</p>
              <div class="interests-tags">
                <span
                  v-for="interest in matchedUser.interests.slice(0, 3)"
                  :key="interest"
                  class="interest-tag"
                >
                  {{ interest }}
                </span>
              </div>
            </div>
          </div>

          <!-- 操作按鈕 -->
          <div class="modal-actions">
            <button class="btn-secondary" @click="handleClose" aria-label="繼續探索">
              繼續探索
            </button>
            <button class="btn-primary" @click="goToMatches" aria-label="查看配對">
              查看配對
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  show: {
    type: Boolean,
    required: true
  },
  matchedUser: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])
const router = useRouter()

const handleClose = () => {
  emit('close')
}

const goToMatches = () => {
  emit('close')
  router.push('/matches')
}
</script>

<style scoped>
/* Modal 覆蓋層 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  padding: var(--space-5);
}

/* Modal 容器 */
.modal-container {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  max-width: min(500px, calc(100vw - 40px));
  width: 100%;
  box-shadow: var(--shadow-xl);
  animation: slideUp var(--duration-slow) var(--easing-out);
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

/* Modal 內容 */
.modal-content {
  padding: 40px 30px 30px;
  text-align: center;
}

/* 配對成功圖示 */
.match-icon {
  margin-bottom: 20px;
  position: relative;
}

/* 背景柔光效果 */
.match-icon::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 120px;
  height: 120px;
  background: radial-gradient(circle, var(--color-like-alpha-20) 0%, transparent 70%);
  border-radius: 50%;
  animation: glow-pulse 2s ease-in-out infinite;
}

.heart-animation {
  font-size: 80px;
  animation: heartBeat 1s ease-in-out infinite;
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 0 15px var(--color-like-alpha-40));
}

@keyframes heartBeat {
  0%, 100% {
    transform: scale(1);
  }
  25% {
    transform: scale(1.1);
  }
  50% {
    transform: scale(1);
  }
  75% {
    transform: scale(1.15);
  }
}

/* 光環脈衝動畫 */
@keyframes glow-pulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.6;
    box-shadow: 0 0 20px var(--color-like-alpha-20);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.3);
    opacity: 0.3;
    box-shadow: 0 0 60px var(--color-like-alpha-40);
  }
}

/* 標題 */
.modal-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-like);
  margin: 0 0 var(--space-3);
}

.modal-subtitle {
  font-size: 16px;
  color: #666;
  margin: 0 0 30px;
}

/* 用戶資訊 */
.user-info {
  margin-bottom: 30px;
}

.user-avatar {
  width: 120px;
  height: 120px;
  margin: 0 auto var(--space-4);
  border-radius: var(--radius-full);
  overflow: hidden;
  border: 4px solid var(--color-like);
  box-shadow: 0 4px 12px var(--color-like-alpha-20);
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
  color: white;
  font-size: 48px;
  font-weight: bold;
}

.user-name {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin: 0 0 5px;
}

.user-age {
  font-size: 16px;
  color: #666;
  margin: 0 0 20px;
}

/* 共同興趣 */
.common-interests {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.interests-title {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: 0 0 10px;
}

.interests-tags {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.interest-tag {
  display: inline-block;
  padding: var(--space-2) var(--space-4);
  background: var(--color-like-alpha-10);
  color: var(--color-like-accessible);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

/* 操作按鈕 */
.modal-actions {
  display: flex;
  gap: 12px;
}

.modal-actions button {
  flex: 1;
  padding: var(--space-4) var(--space-5);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--duration-slow) var(--easing-default);
}

.btn-primary {
  background: var(--color-like-gradient);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--color-like-alpha-40);
}

.btn-secondary {
  background: var(--color-background-light);
  color: var(--color-text-muted);
}

.btn-secondary:hover {
  background: var(--color-border);
}

/* Modal 過渡效果 */
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from, .modal-leave-to {
  opacity: 0;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .modal-content {
    padding: 30px 20px 20px;
  }

  .modal-title {
    font-size: 24px;
  }

  .user-avatar {
    width: 100px;
    height: 100px;
  }

  .user-name {
    font-size: 20px;
  }

  .modal-actions {
    flex-direction: column;
  }
}
</style>
