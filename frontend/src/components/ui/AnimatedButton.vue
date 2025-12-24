<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="['animated-btn', variant, { 'is-loading': loading }]"
    :aria-busy="loading"
    :aria-label="loading ? loadingText : undefined"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="loader-wrapper" role="status" aria-live="polite">
      <span class="loader" aria-hidden="true"></span>
      <span class="sr-only">{{ loadingText }}</span>
    </span>
    <span v-else class="btn-content">
      <slot></slot>
    </span>
    <span class="shine" aria-hidden="true"></span>
  </button>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'button'
  },
  variant: {
    type: String,
    default: 'primary', // primary, secondary, success, danger, ghost
    validator: (value) => ['primary', 'secondary', 'success', 'danger', 'ghost'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  loadingText: {
    type: String,
    default: '處理中，請稍候'
  }
})

defineEmits(['click'])
</script>

<style scoped>
/* Screen Reader Only - 僅對螢幕閱讀器可見 */
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

.animated-btn {
  position: relative;
  padding: 14px 32px;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  isolation: isolate;
}

.animated-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  transform: translateX(-100%);
  transition: transform 0.6s;
}

.animated-btn:hover::before {
  transform: translateX(100%);
}

.animated-btn:active {
  transform: scale(0.98);
}

.btn-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s;
}

.animated-btn:hover .shine {
  left: 100%;
}

/* Variants */
.animated-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.animated-btn.primary:hover:not(:disabled) {
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
  transform: translateY(-2px);
}

.animated-btn.secondary {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.animated-btn.secondary:hover:not(:disabled) {
  box-shadow: 0 8px 25px rgba(245, 87, 108, 0.4);
  transform: translateY(-2px);
}

.animated-btn.success {
  background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%);
  color: white;
}

.animated-btn.success:hover:not(:disabled) {
  box-shadow: 0 8px 25px rgba(76, 175, 80, 0.4);
  transform: translateY(-2px);
}

.animated-btn.danger {
  background: linear-gradient(135deg, #F44336 0%, #E91E63 100%);
  color: white;
}

.animated-btn.danger:hover:not(:disabled) {
  box-shadow: 0 8px 25px rgba(244, 67, 54, 0.4);
  transform: translateY(-2px);
}

.animated-btn.ghost {
  background: transparent;
  border: 3px solid #5a5a9a;
  color: #4a4a8a;
  font-weight: 700;
  box-shadow: none;
}

.animated-btn.ghost:hover:not(:disabled) {
  background: #5a5a9a;
  border-color: #5a5a9a;
  color: white;
  box-shadow: 0 8px 25px rgba(90, 90, 154, 0.3);
}

/* Disabled state */
.animated-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

/* Loading state */
.animated-btn.is-loading {
  cursor: wait;
}

.loader-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.loader {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  display: inline-block;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Ripple effect */
.animated-btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

.animated-btn:active::after {
  width: 300px;
  height: 300px;
  transition: width 0s, height 0s;
}
</style>
