<!--
  SkeletonCard.vue
  卡片骨架載入器 - 用於 Discovery 頁面

  使用方式:
  <SkeletonCard />
  <SkeletonCard :stacked="true" :index="0" />
-->
<template>
  <div
    class="skeleton-card"
    :class="{ stacked }"
    :style="stackedStyle"
    role="status"
    aria-label="載入中"
  >
    <!-- 圖片區域 -->
    <div class="skeleton-image">
      <div class="skeleton-shimmer"></div>

      <!-- 配對分數位置 -->
      <div class="skeleton-badge top-right">
        <div class="skeleton-shimmer"></div>
      </div>

      <!-- 舉報按鈕位置 -->
      <div class="skeleton-badge top-left">
        <div class="skeleton-shimmer"></div>
      </div>
    </div>

    <!-- 資訊區域 -->
    <div class="skeleton-info">
      <!-- 名字和年齡 -->
      <div class="skeleton-header">
        <div class="skeleton-name">
          <div class="skeleton-shimmer"></div>
        </div>
        <div class="skeleton-age">
          <div class="skeleton-shimmer"></div>
        </div>
      </div>

      <!-- 距離 -->
      <div class="skeleton-distance">
        <div class="skeleton-shimmer"></div>
      </div>

      <!-- 興趣標籤 -->
      <div class="skeleton-tags">
        <div class="skeleton-tag">
          <div class="skeleton-shimmer"></div>
        </div>
        <div class="skeleton-tag">
          <div class="skeleton-shimmer"></div>
        </div>
        <div class="skeleton-tag">
          <div class="skeleton-shimmer"></div>
        </div>
      </div>

      <!-- 簡介 -->
      <div class="skeleton-bio">
        <div class="skeleton-line long">
          <div class="skeleton-shimmer"></div>
        </div>
        <div class="skeleton-line medium">
          <div class="skeleton-shimmer"></div>
        </div>
      </div>
    </div>

    <span class="sr-only">正在載入候選人資料...</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /**
   * 是否為堆疊卡片（多張卡片視覺效果）
   */
  stacked: {
    type: Boolean,
    default: false
  },
  /**
   * 堆疊索引（影響縮放和位移）
   */
  index: {
    type: Number,
    default: 0
  }
})

const stackedStyle = computed(() => {
  if (!props.stacked) return {}

  const scales = [1, 0.95, 0.9]
  const translates = [0, 10, 20]
  const opacities = [1, 0.8, 0.6]
  const zIndexes = [10, 1, 0]

  return {
    transform: `scale(${scales[props.index] || 0.9}) translateY(${translates[props.index] || 20}px)`,
    opacity: opacities[props.index] || 0.6,
    zIndex: zIndexes[props.index] || 0
  }
})
</script>

<style scoped>
.skeleton-card {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.8);
}

.skeleton-card.stacked {
  position: absolute;
  width: 100%;
  height: 100%;
  transition:
    transform var(--duration-slow) var(--easing-default),
    opacity var(--duration-slow) var(--easing-default);
}

/* 圖片骨架 */
.skeleton-image {
  position: relative;
  width: 100%;
  height: 360px;
  background: linear-gradient(135deg, var(--color-primary-100) 0%, var(--color-primary-50) 100%);
  overflow: hidden;
}

/* 徽章骨架 */
.skeleton-badge {
  position: absolute;
  width: 80px;
  height: 36px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.skeleton-badge.top-right {
  top: var(--space-5);
  right: var(--space-5);
}

.skeleton-badge.top-left {
  top: var(--space-5);
  left: var(--space-5);
  width: var(--touch-target-min);
  height: var(--touch-target-min);
  border-radius: var(--radius-full);
}

/* 資訊區域骨架 */
.skeleton-info {
  padding: var(--space-5);
}

.skeleton-header {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.skeleton-name {
  width: 120px;
  height: 28px;
  background: var(--color-primary-50);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.skeleton-age {
  width: 40px;
  height: 24px;
  background: var(--color-primary-50);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.skeleton-distance {
  width: 80px;
  height: 18px;
  background: var(--color-primary-50);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-4);
  overflow: hidden;
}

.skeleton-tags {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.skeleton-tag {
  width: 60px;
  height: 28px;
  background: var(--color-primary-50);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.skeleton-tag:nth-child(2) {
  width: 80px;
}

.skeleton-tag:nth-child(3) {
  width: 50px;
}

.skeleton-bio {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.skeleton-line {
  height: 16px;
  background: var(--color-primary-50);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.skeleton-line.long {
  width: 100%;
}

.skeleton-line.medium {
  width: 70%;
}

/* 閃爍動畫 */
.skeleton-shimmer {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.5) 50%,
    transparent 100%
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

/* Screen Reader Only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* 響應式 */
@media (max-width: 768px) {
  .skeleton-image {
    height: 350px;
  }
}

/* 減少動態效果偏好 */
@media (prefers-reduced-motion: reduce) {
  .skeleton-shimmer {
    animation: none;
  }
}
</style>
