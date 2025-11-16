<template>
  <div class="glass-card" :class="[variant, { hoverable }]">
    <div v-if="$slots.icon" class="card-icon">
      <slot name="icon"></slot>
    </div>
    <div class="card-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'default', // default, primary, success, warning, danger
    validator: (value) => ['default', 'primary', 'success', 'warning', 'danger'].includes(value)
  },
  hoverable: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.glass-card {
  position: relative;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.8);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.glass-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transition: left 0.5s;
}

.glass-card.hoverable:hover::before {
  left: 100%;
}

.glass-card.hoverable:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

/* Variants */
.glass-card.primary {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
  border: 2px solid rgba(102, 126, 234, 0.3);
}

.glass-card.success {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.1), rgba(102, 187, 106, 0.1));
  border: 2px solid rgba(76, 175, 80, 0.3);
}

.glass-card.warning {
  background: linear-gradient(135deg, rgba(255, 152, 0, 0.1), rgba(255, 193, 7, 0.1));
  border: 2px solid rgba(255, 152, 0, 0.3);
}

.glass-card.danger {
  background: linear-gradient(135deg, rgba(244, 67, 54, 0.1), rgba(233, 30, 99, 0.1));
  border: 2px solid rgba(244, 67, 54, 0.3);
}

.card-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  text-align: center;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.card-content {
  position: relative;
  z-index: 1;
}
</style>
