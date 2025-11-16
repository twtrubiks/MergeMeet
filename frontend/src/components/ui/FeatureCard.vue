<template>
  <div class="feature-card">
    <div class="feature-header">
      <h4>{{ title }}</h4>
      <div class="feature-badge">{{ badge }}</div>
    </div>
    <ul class="feature-list">
      <li v-for="(item, index) in items" :key="index" class="feature-item">
        <span class="check-icon">✓</span>
        <span>{{ item }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  badge: {
    type: String,
    default: ''
  },
  items: {
    type: Array,
    required: true
  }
})
</script>

<style scoped>
.feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
  animation: slideIn 0.5s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.feature-card:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.4);
  transform: translateY(-4px);
}

.feature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.feature-header h4 {
  margin: 0;
  color: white;
  font-size: 1.1rem;
  font-weight: 700;
}

.feature-badge {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  color: rgba(255, 255, 255, 0.95);
  font-size: 0.95rem;
  transition: all 0.2s ease;
}

.feature-item:hover {
  padding-left: 8px;
  color: white;
}

.check-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: rgba(76, 175, 80, 0.8);
  color: white;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: bold;
  flex-shrink: 0;
}
</style>
