<template>
  <div class="chat-image-picker">
    <!-- 圖片選擇按鈕 -->
    <n-button text @click="triggerFileInput" :disabled="disabled">
      <template #icon>
        <n-icon size="24"><ImageOutline /></n-icon>
      </template>
    </n-button>

    <!-- 隱藏的檔案輸入 -->
    <input
      ref="fileInputRef"
      type="file"
      accept="image/jpeg,image/png,image/gif,image/webp"
      @change="handleFileSelect"
      style="display: none"
    />

    <!-- 預覽 Modal -->
    <n-modal
      v-model:show="showPreview"
      preset="card"
      :title="isGif ? '發送 GIF' : '發送圖片'"
      style="width: 90%; max-width: 500px"
      :bordered="false"
    >
      <div class="image-preview">
        <img :src="previewUrl" :alt="isGif ? 'GIF 預覽' : '圖片預覽'" />
      </div>

      <template #footer>
        <div class="preview-actions">
          <n-button @click="cancelUpload">取消</n-button>
          <n-button type="primary" :loading="uploading" @click="confirmUpload">
            發送
          </n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { NButton, NIcon, NModal, useMessage } from 'naive-ui'
import { ImageOutline } from '@vicons/ionicons5'
import { useChatStore } from '@/stores/chat'

const props = defineProps({
  matchId: {
    type: String,
    required: true
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['image-sent'])

const message = useMessage()
const chatStore = useChatStore()

const fileInputRef = ref(null)
const showPreview = ref(false)
const previewUrl = ref('')
const selectedFile = ref(null)
const uploading = ref(false)

// 判斷是否為 GIF
const isGif = computed(() => {
  return selectedFile.value?.type === 'image/gif'
})

// 觸發檔案選擇
const triggerFileInput = () => {
  fileInputRef.value?.click()
}

// 處理檔案選擇
const handleFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  // 驗證檔案類型
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    message.error('不支援的圖片格式，僅支援 JPEG, PNG, GIF, WebP')
    resetFileInput()
    return
  }

  // 驗證檔案大小 (5MB)
  const maxSize = 5 * 1024 * 1024
  if (file.size > maxSize) {
    message.error('檔案過大，最大允許 5MB')
    resetFileInput()
    return
  }

  // 設定預覽
  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  showPreview.value = true
}

// 重設檔案輸入
const resetFileInput = () => {
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
  selectedFile.value = null
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

// 取消上傳
const cancelUpload = () => {
  showPreview.value = false
  resetFileInput()
}

// 確認上傳並發送
const confirmUpload = async () => {
  if (!selectedFile.value || !props.matchId) return

  uploading.value = true

  try {
    // 上傳圖片
    const uploadResult = await chatStore.uploadChatImage(props.matchId, selectedFile.value)

    // 發送圖片訊息
    await chatStore.sendImageMessage(props.matchId, uploadResult)

    message.success('圖片已發送')
    emit('image-sent', uploadResult)

    // 關閉預覽並重設
    showPreview.value = false
    resetFileInput()
  } catch (error) {
    message.error(error.message || '發送圖片失敗')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.chat-image-picker {
  display: flex;
  align-items: center;
}

.image-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  max-height: 400px;
  overflow: hidden;
  border-radius: 8px;
  background-color: #f5f5f5;
}

.image-preview img {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
