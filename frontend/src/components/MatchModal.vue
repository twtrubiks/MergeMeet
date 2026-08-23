<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="show"
        class="modal-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="配對成功"
        @click="handleClose"
        @keydown.escape="handleClose"
      >
        <!-- 慶祝粒子 -->
        <div class="confetti" aria-hidden="true">
          <span v-for="i in 20" :key="i" class="particle" :style="particleStyle(i)"></span>
        </div>

        <div class="modal-container" @click.stop>
          <div class="modal-content">
            <!-- MergeMeet 品牌視覺簽名：雙心交疊 -->
            <div class="brand-hearts" aria-hidden="true">
              <div class="heart-left">❤</div>
              <div class="heart-right">❤</div>
              <div class="merge-spark"></div>
            </div>

            <!-- 標題 -->
            <h2 class="modal-title">It's a Match!</h2>
            <p class="modal-subtitle">太棒了，你們互相喜歡對方</p>

            <!-- 用戶資訊 -->
            <div v-if="matchedUser" class="user-info">
              <div class="user-avatar">
                <img
                  v-if="matchedUser.photos?.length"
                  :src="matchedUser.photos[0]"
                  :alt="matchedUser.display_name"
                />
                <div v-else class="avatar-placeholder">
                  {{ matchedUser.display_name?.[0] }}
                </div>
              </div>
              <h3 class="user-name">{{ matchedUser.display_name }}</h3>
              <p v-if="matchedUser.age" class="user-age">{{ matchedUser.age }} 歲</p>

              <!-- 共同興趣（後端依瀏覽者計算，無共同興趣則不顯示） -->
              <div
                v-if="matchedUser.common_interests && matchedUser.common_interests.length > 0"
                class="common-interests"
              >
                <p class="interests-title">你們都喜歡</p>
                <div class="interests-tags">
                  <span
                    v-for="interest in matchedUser.common_interests.slice(0, 3)"
                    :key="interest"
                    class="interest-tag"
                  >
                    {{ interest }}
                  </span>
                  <span v-if="matchedUser.common_interests.length > 3" class="interest-tag">
                    +{{ matchedUser.common_interests.length - 3 }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 操作按鈕 -->
            <div class="modal-actions">
              <button class="btn-secondary" aria-label="繼續探索" @click="handleClose">
                繼續探索
              </button>
              <button class="btn-primary" aria-label="開始聊天" @click="goToMatches">
                開始聊天
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { useRouter } from 'vue-router'

defineProps({
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

/**
 * 為每個慶祝粒子生成隨機樣式
 */
const particleStyle = (i) => {
  const hue = (i * 18) % 360
  const left = Math.random() * 100
  const delay = Math.random() * 0.6
  const duration = 1.5 + Math.random() * 1
  const size = 6 + Math.random() * 6
  return {
    '--hue': hue,
    '--left': `${left}%`,
    '--delay': `${delay}s`,
    '--duration': `${duration}s`,
    '--size': `${size}px`
  }
}
</script>

<style scoped>
/* Modal 覆蓋層 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  padding: var(--space-5);
  overflow: hidden;
}

/* 慶祝粒子 */
.confetti {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.particle {
  position: absolute;
  top: -10px;
  left: var(--left);
  width: var(--size);
  height: var(--size);
  border-radius: 2px;
  background: hsl(var(--hue), 80%, 65%);
  animation: confetti-fall var(--duration) var(--delay) ease-out forwards;
  opacity: 0;
}

@keyframes confetti-fall {
  0% {
    opacity: 1;
    transform: translateY(0) rotate(0deg);
  }
  100% {
    opacity: 0;
    transform: translateY(100vh) rotate(720deg);
  }
}

/* Modal 容器 */
.modal-container {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  max-width: min(440px, calc(100vw - 40px));
  width: 100%;
  box-shadow: var(--shadow-xl);
  animation: modal-enter 0.5s var(--easing-out);
  position: relative;
  z-index: 1;
}

@keyframes modal-enter {
  0% {
    transform: scale(0.8) translateY(30px);
    opacity: 0;
  }
  60% {
    transform: scale(1.02);
    opacity: 1;
  }
  100% {
    transform: scale(1) translateY(0);
  }
}

/* Modal 內容 */
.modal-content {
  padding: var(--space-10) var(--space-8) var(--space-8);
  text-align: center;
}

/* ========================================
   品牌視覺簽名：雙心交疊 (MergeMeet)
   兩顆心從左右滑入、交疊、產生火花
   ======================================== */
.brand-hearts {
  position: relative;
  height: 80px;
  margin-bottom: var(--space-6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.heart-left,
.heart-right {
  font-size: 48px;
  position: absolute;
  animation-fill-mode: forwards;
  filter: drop-shadow(0 4px 12px var(--color-like-alpha-40));
}

.heart-left {
  color: var(--color-like);
  animation: merge-left 0.8s var(--easing-out) forwards;
}

.heart-right {
  color: var(--color-primary-400);
  animation: merge-right 0.8s var(--easing-out) forwards;
}

@keyframes merge-left {
  0% {
    transform: translateX(-60px) rotate(-20deg) scale(0.6);
    opacity: 0;
  }
  60% {
    opacity: 1;
  }
  100% {
    transform: translateX(-12px) rotate(-8deg) scale(1);
    opacity: 1;
  }
}

@keyframes merge-right {
  0% {
    transform: translateX(60px) rotate(20deg) scale(0.6);
    opacity: 0;
  }
  60% {
    opacity: 1;
  }
  100% {
    transform: translateX(12px) rotate(8deg) scale(1);
    opacity: 1;
  }
}

/* 交疊時的火花效果 */
.merge-spark {
  position: absolute;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: radial-gradient(circle, rgba(255, 255, 255, 0.9) 0%, transparent 70%);
  animation: spark 0.6s 0.6s ease-out forwards;
  opacity: 0;
}

@keyframes spark {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  40% {
    transform: scale(3);
    opacity: 1;
  }
  100% {
    transform: scale(5);
    opacity: 0;
  }
}

/* 標題 */
.modal-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-extrabold);
  color: var(--color-like);
  margin: 0 0 var(--space-2);
  letter-spacing: -0.5px;
}

.modal-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-8);
}

/* 用戶資訊 */
.user-info {
  margin-bottom: var(--space-8);
}

.user-avatar {
  width: 110px;
  height: 110px;
  margin: 0 auto var(--space-4);
  border-radius: var(--radius-full);
  overflow: hidden;
  border: 4px solid var(--color-like);
  box-shadow: 0 4px 20px var(--color-like-alpha-20);
  animation: avatar-pop 0.4s 0.8s var(--easing-out) both;
}

@keyframes avatar-pop {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  70% {
    transform: scale(1.08);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
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
  background: var(--color-like-gradient);
  color: white;
  font-size: var(--font-size-5xl);
  font-weight: var(--font-weight-bold);
}

.user-name {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
  animation: text-fade 0.4s 1s ease both;
}

.user-age {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-5);
  animation: text-fade 0.4s 1.1s ease both;
}

@keyframes text-fade {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 共同興趣 */
.common-interests {
  margin-top: var(--space-5);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border-light);
  animation: text-fade 0.4s 1.2s ease both;
}

.interests-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-3);
}

.interests-tags {
  display: flex;
  gap: var(--space-2);
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
  gap: var(--space-3);
  animation: text-fade 0.4s 1.3s ease both;
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
  min-height: var(--touch-target-min);
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

.modal-actions button:focus-visible {
  outline: 3px solid var(--color-primary-600);
  outline-offset: 2px;
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
  .modal-content {
    padding: var(--space-8) var(--space-5) var(--space-5);
  }

  .modal-title {
    font-size: var(--font-size-2xl);
  }

  .user-avatar {
    width: 90px;
    height: 90px;
  }

  .user-name {
    font-size: var(--font-size-xl);
  }

  .modal-actions {
    flex-direction: column;
  }

  .heart-left,
  .heart-right {
    font-size: 40px;
  }
}

/* 無障礙：減少動態效果 */
@media (prefers-reduced-motion: reduce) {
  .particle {
    animation: none;
    display: none;
  }

  .heart-left,
  .heart-right,
  .merge-spark,
  .user-avatar,
  .user-name,
  .user-age,
  .common-interests,
  .modal-actions {
    animation: none;
    opacity: 1;
  }

  .modal-container {
    animation: none;
  }
}
</style>
