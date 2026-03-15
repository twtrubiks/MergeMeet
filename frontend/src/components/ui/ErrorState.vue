<!--
  ErrorState.vue
  錯誤狀態元件 - 提供可操作的錯誤顯示

  使用方式:
  <ErrorState
    title="無法載入資料"
    message="請檢查網路連線後重試"
    @retry="handleRetry"
  />

  <ErrorState
    variant="warning"
    title="找不到資料"
    :show-retry="false"
  />
-->
<template>
  <div class="error-state" :class="variant" role="alert" aria-live="polite">
    <!-- 圖標 -->
    <div class="error-icon" aria-hidden="true">
      <n-icon :size="iconSize">
        <component :is="iconComponent" />
      </n-icon>
    </div>

    <!-- 標題 -->
    <h3 class="error-title">{{ title }}</h3>

    <!-- 描述訊息 -->
    <p v-if="message" class="error-message">{{ message }}</p>

    <!-- 操作按鈕 -->
    <div v-if="showRetry" class="error-actions">
      <AnimatedButton :variant="buttonVariant" @click="$emit('retry')">
        <Icon name="refresh" size="sm" decorative />
        {{ retryText }}
      </AnimatedButton>
    </div>

    <!-- 自訂操作插槽 -->
    <div v-if="$slots.actions" class="error-actions">
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
// 保留 NIcon 和圖標導入用於動態 iconComponent（依據 variant 切換圖標）
import { AlertCircleOutline, WarningOutline, InformationCircleOutline } from '@vicons/ionicons5'
import AnimatedButton from './AnimatedButton.vue'
import Icon from './Icon.vue'

const props = defineProps({
  /**
   * 錯誤標題
   */
  title: {
    type: String,
    default: '發生錯誤'
  },
  /**
   * 錯誤描述訊息
   */
  message: {
    type: String,
    default: ''
  },
  /**
   * 變體類型
   * @type {'error' | 'warning' | 'info'}
   */
  variant: {
    type: String,
    default: 'error',
    validator: (value) => ['error', 'warning', 'info'].includes(value)
  },
  /**
   * 是否顯示重試按鈕
   */
  showRetry: {
    type: Boolean,
    default: true
  },
  /**
   * 重試按鈕文字
   */
  retryText: {
    type: String,
    default: '重試'
  },
  /**
   * 圖標大小
   */
  iconSize: {
    type: Number,
    default: 56
  }
})

defineEmits(['retry'])

// 根據變體選擇圖標
const iconComponent = computed(() => {
  const icons = {
    error: AlertCircleOutline,
    warning: WarningOutline,
    info: InformationCircleOutline
  }
  return icons[props.variant]
})

// 根據變體選擇按鈕樣式
const buttonVariant = computed(() => {
  const variants = {
    error: 'danger',
    warning: 'secondary',
    info: 'primary'
  }
  return variants[props.variant]
})
</script>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-12) var(--space-6);
  min-height: 300px;
  animation: fadeIn 0.4s var(--easing-out);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 圖標 */
.error-icon {
  margin-bottom: var(--space-5);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.9;
  }
}

/* 變體顏色 */
.error-state.error .error-icon {
  color: var(--color-error-500);
}

.error-state.warning .error-icon {
  color: var(--color-warning-500);
}

.error-state.info .error-icon {
  color: var(--color-primary-500);
}

/* 標題 */
.error-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
}

/* 訊息 */
.error-message {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-6);
  max-width: 400px;
  line-height: var(--line-height-relaxed);
}

/* 操作按鈕 */
.error-actions {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
  justify-content: center;
}

/* 響應式 */
@media (max-width: 480px) {
  .error-state {
    padding: var(--space-8) var(--space-4);
    min-height: 250px;
  }

  .error-title {
    font-size: var(--font-size-lg);
  }

  .error-message {
    font-size: var(--font-size-sm);
  }
}

/* 減少動態效果偏好 */
@media (prefers-reduced-motion: reduce) {
  .error-icon {
    animation: none;
  }
}
</style>
