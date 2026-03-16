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
.animated-btn {
  position: relative;
  padding: 14px 32px;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  overflow: hidden;
  transition: all var(--duration-slow) var(--easing-default);
  box-shadow: var(--shadow-button);
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

.animated-btn:focus-visible {
  outline: 3px solid var(--color-primary-600);
  outline-offset: 2px;
}

.animated-btn:active {
  transform: scale(0.98);
}

.btn-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* Variants */
.animated-btn.primary {
  background: var(--color-primary-gradient);
  color: white;
}

.animated-btn.primary:hover:not(:disabled) {
  box-shadow: var(--shadow-button-hover);
  transform: translateY(-2px);
}

.animated-btn.secondary {
  background: var(--color-secondary-gradient);
  color: white;
}

.animated-btn.secondary:hover:not(:disabled) {
  box-shadow: 0 8px 25px rgba(245, 87, 108, 0.4);
  transform: translateY(-2px);
}

.animated-btn.success {
  background: var(--color-success-gradient);
  color: white;
}

.animated-btn.success:hover:not(:disabled) {
  box-shadow: 0 8px 25px rgba(76, 175, 80, 0.4);
  transform: translateY(-2px);
}

.animated-btn.danger {
  background: var(--color-error-gradient);
  color: white;
}

.animated-btn.danger:hover:not(:disabled) {
  box-shadow: 0 8px 25px rgba(244, 67, 54, 0.4);
  transform: translateY(-2px);
}

.animated-btn.ghost {
  background: transparent;
  border: 3px solid var(--color-primary-600);
  color: var(--color-primary-700);
  font-weight: var(--font-weight-bold);
  box-shadow: none;
}

.animated-btn.ghost:hover:not(:disabled) {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  color: white;
  box-shadow: 0 8px 25px var(--color-primary-alpha-30);
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
  border-radius: var(--radius-full);
  display: inline-block;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Ripple effect */
.animated-btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.4);
  transform: translate(-50%, -50%);
  transition:
    width 0.6s,
    height 0.6s;
}

.animated-btn:active::after {
  width: 300px;
  height: 300px;
  transition:
    width 0s,
    height 0s;
}
</style>
