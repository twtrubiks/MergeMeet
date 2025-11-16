<template>
  <span class="badge" :class="[variant, size]">
    <slot></slot>
  </span>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'default', // default, primary, success, warning, danger, info
    validator: (value) => ['default', 'primary', 'success', 'warning', 'danger', 'info'].includes(value)
  },
  size: {
    type: String,
    default: 'medium', // small, medium, large
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  }
})
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  transition: all 0.2s ease;
}

/* Sizes */
.badge.small {
  padding: 4px 8px;
  font-size: 0.7rem;
}

.badge.medium {
  padding: 6px 12px;
  font-size: 0.75rem;
}

.badge.large {
  padding: 8px 16px;
  font-size: 0.85rem;
}

/* Variants */
.badge.default {
  background: #f5f5f5;
  color: #666;
}

.badge.primary {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
  color: #667eea;
  border: 1px solid rgba(102, 126, 234, 0.3);
}

.badge.success {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.15), rgba(102, 187, 106, 0.15));
  color: #4CAF50;
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.badge.warning {
  background: linear-gradient(135deg, rgba(255, 152, 0, 0.15), rgba(255, 193, 7, 0.15));
  color: #FF9800;
  border: 1px solid rgba(255, 152, 0, 0.3);
}

.badge.danger {
  background: linear-gradient(135deg, rgba(244, 67, 54, 0.15), rgba(233, 30, 99, 0.15));
  color: #F44336;
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.badge.info {
  background: linear-gradient(135deg, rgba(33, 150, 243, 0.15), rgba(3, 169, 244, 0.15));
  color: #2196F3;
  border: 1px solid rgba(33, 150, 243, 0.3);
}

.badge:hover {
  transform: scale(1.05);
}
</style>
