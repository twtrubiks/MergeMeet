<!--
  SkeletonListItem.vue
  列表項目骨架載入器 - 用於 ChatList 和 Matches 頁面

  使用方式:
  <SkeletonListItem />
  <SkeletonListItem variant="chat" />
  <SkeletonListItem variant="match" />
-->
<template>
  <div
    class="skeleton-list-item"
    :class="variant"
    role="status"
    aria-label="載入中"
  >
    <!-- 頭像 -->
    <div class="skeleton-avatar">
      <div class="skeleton-shimmer"></div>
    </div>

    <!-- 內容區域 -->
    <div class="skeleton-content">
      <!-- 名字行 -->
      <div class="skeleton-row">
        <div class="skeleton-name">
          <div class="skeleton-shimmer"></div>
        </div>
        <div v-if="variant === 'chat'" class="skeleton-time">
          <div class="skeleton-shimmer"></div>
        </div>
      </div>

      <!-- 訊息/描述行 -->
      <div class="skeleton-message">
        <div class="skeleton-shimmer"></div>
      </div>

      <!-- 額外標籤（用於 match variant） -->
      <div v-if="variant === 'match'" class="skeleton-tags">
        <div class="skeleton-tag">
          <div class="skeleton-shimmer"></div>
        </div>
        <div class="skeleton-tag">
          <div class="skeleton-shimmer"></div>
        </div>
      </div>
    </div>

    <!-- 未讀標記 (chat variant) -->
    <div v-if="variant === 'chat'" class="skeleton-badge-dot">
      <div class="skeleton-shimmer"></div>
    </div>

    <span class="sr-only">正在載入資料...</span>
  </div>
</template>

<script setup>
defineProps({
  /**
   * 變體類型
   * @type {'chat' | 'match' | 'default'}
   */
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'chat', 'match'].includes(value)
  }
})
</script>

<style scoped>
.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border-bottom: 1px solid var(--color-border-light);
}

.skeleton-list-item.chat {
  padding: var(--space-3) var(--space-4);
}

.skeleton-list-item.match {
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border-bottom: none;
  box-shadow: var(--shadow-sm);
}

/* 頭像骨架 */
.skeleton-avatar {
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  background: var(--color-primary-50);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.skeleton-list-item.match .skeleton-avatar {
  width: 80px;
  height: 80px;
  margin-bottom: var(--space-2);
}

/* 內容區域 */
.skeleton-content {
  flex: 1;
  min-width: 0;
}

.skeleton-list-item.match .skeleton-content {
  width: 100%;
}

.skeleton-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.skeleton-list-item.match .skeleton-row {
  justify-content: center;
}

/* 名字骨架 */
.skeleton-name {
  width: 100px;
  height: 18px;
  background: var(--color-primary-50);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.skeleton-list-item.match .skeleton-name {
  width: 80px;
}

/* 時間骨架 */
.skeleton-time {
  width: 40px;
  height: 14px;
  background: var(--color-primary-50);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

/* 訊息骨架 */
.skeleton-message {
  width: 80%;
  height: 14px;
  background: var(--color-primary-50);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.skeleton-list-item.match .skeleton-message {
  width: 60%;
  margin: 0 auto;
}

/* 標籤骨架 */
.skeleton-tags {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.skeleton-tag {
  width: 50px;
  height: 22px;
  background: var(--color-primary-50);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* 未讀標記骨架 */
.skeleton-badge-dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  background: var(--color-primary-100);
  border-radius: var(--radius-full);
  overflow: hidden;
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

/* 減少動態效果偏好 */
@media (prefers-reduced-motion: reduce) {
  .skeleton-shimmer {
    animation: none;
  }
}
</style>
