<template>
  <n-modal
    :show="show"
    @update:show="$emit('update:show', $event)"
    :mask-closable="true"
    class="image-preview-modal"
  >
    <div class="image-preview-container" @click="handleBackgroundClick">
      <!-- 關閉按鈕 -->
      <n-button
        text
        class="close-button"
        @click="$emit('update:show', false)"
      >
        <template #icon>
          <n-icon size="28"><CloseOutline /></n-icon>
        </template>
      </n-button>

      <!-- 圖片 -->
      <img
        :src="imageUrl"
        alt="圖片預覽"
        class="preview-image"
        @click.stop
      />
    </div>
  </n-modal>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { NModal, NButton, NIcon } from 'naive-ui'
import { CloseOutline } from '@vicons/ionicons5'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  imageUrl: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:show'])

// 點擊背景關閉
const handleBackgroundClick = (e) => {
  if (e.target.classList.contains('image-preview-container')) {
    emit('update:show', false)
  }
}

// 監聽 ESC 鍵關閉
const handleKeydown = (e) => {
  if (e.key === 'Escape' && props.show) {
    emit('update:show', false)
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.image-preview-modal {
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-preview-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.9);
  cursor: pointer;
}

.close-button {
  position: absolute;
  top: 16px;
  right: 16px;
  color: white;
  z-index: 10;
  cursor: pointer;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.close-button:hover {
  opacity: 1;
}

.preview-image {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  cursor: default;
  border-radius: 4px;
}
</style>
