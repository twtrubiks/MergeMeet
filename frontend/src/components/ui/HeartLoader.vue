<template>
  <div
    class="heart-loader-container"
    role="status"
    aria-live="polite"
    aria-busy="true"
    :aria-label="text || '載入中，請稍候'"
  >
    <div class="heart-loader" aria-hidden="true">
      <div class="heart"></div>
      <div class="heart"></div>
      <div class="heart"></div>
    </div>
    <p v-if="text" class="loader-text" aria-hidden="true">{{ text }}</p>
    <!-- 為螢幕閱讀器提供的隱藏文字 -->
    <span class="sr-only">{{ text || '載入中，請稍候' }}</span>
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    default: ''
  }
})
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

.heart-loader-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 40px;
}

.heart-loader {
  display: flex;
  gap: 15px;
  align-items: center;
}

.heart {
  position: relative;
  width: 20px;
  height: 20px;
  transform: rotate(-45deg);
  animation: heartBeat 1.2s infinite ease-in-out;
}

.heart::before,
.heart::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
  border-radius: 50%;
}

.heart::before {
  top: -10px;
  left: 0;
}

.heart::after {
  top: 0;
  left: 10px;
}

.heart:nth-child(1) {
  animation-delay: 0s;
}

.heart:nth-child(2) {
  animation-delay: 0.2s;
}

.heart:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes heartBeat {
  0%, 100% {
    transform: rotate(-45deg) scale(0.8);
    opacity: 0.5;
  }
  50% {
    transform: rotate(-45deg) scale(1.2);
    opacity: 1;
  }
}

.loader-text {
  font-size: 1rem;
  color: #666;
  font-weight: 500;
  animation: fadeInOut 1.5s infinite;
}

@keyframes fadeInOut {
  0%, 100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}
</style>
