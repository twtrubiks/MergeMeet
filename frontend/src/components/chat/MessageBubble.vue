<template>
  <div
    :class="[
      'message-bubble',
      isOwn ? 'message-own' : 'message-other'
    ]"
  >
    <!-- 對方頭像 (只在對方訊息顯示) -->
    <div v-if="!isOwn && showAvatar" class="message-avatar">
      <n-avatar
        :src="otherUserAvatar"
        :fallback-src="defaultAvatar"
        size="small"
        round
      />
    </div>

    <!-- 訊息內容 -->
    <div class="message-content-wrapper">
      <!-- 文字訊息（自己的訊息可以右鍵刪除） -->
      <template v-if="isTextMessage">
        <n-dropdown
          v-if="isOwn"
          trigger="manual"
          :show="showDropdown"
          :options="dropdownOptions"
          @select="handleDropdownSelect"
          @clickoutside="showDropdown = false"
        >
          <div
            :class="[
              'message-content',
              isOwn ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-900'
            ]"
            @contextmenu.prevent="handleContextMenu"
          >
            {{ message.content }}
          </div>
        </n-dropdown>

        <!-- 對方的訊息（不可刪除） -->
        <div
          v-else
          :class="[
            'message-content',
            isOwn ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-900'
          ]"
        >
          {{ message.content }}
        </div>
      </template>

      <!-- 圖片/GIF 訊息 -->
      <template v-else-if="isImageMessage">
        <n-dropdown
          v-if="isOwn"
          trigger="manual"
          :show="showDropdown"
          :options="dropdownOptions"
          @select="handleDropdownSelect"
          @clickoutside="showDropdown = false"
        >
          <div
            class="message-image"
            @click="handleImageClick"
            @contextmenu.prevent="handleContextMenu"
          >
            <img
              :src="imageContent.thumbnail_url"
              :alt="isGif ? 'GIF' : '圖片'"
              loading="lazy"
            />
            <div v-if="isGif" class="gif-badge">GIF</div>
          </div>
        </n-dropdown>

        <!-- 對方的圖片（不可刪除） -->
        <div
          v-else
          class="message-image"
          @click="handleImageClick"
        >
          <img
            :src="imageContent.thumbnail_url"
            :alt="isGif ? 'GIF' : '圖片'"
            loading="lazy"
          />
          <div v-if="isGif" class="gif-badge">GIF</div>
        </div>
      </template>

      <!-- 訊息資訊 (時間、已讀狀態) -->
      <div class="message-info">
        <span class="message-time">{{ formattedTime }}</span>
        <span v-if="isOwn && message.is_read" class="message-status">
          ✓✓ 已讀
        </span>
        <span v-else-if="isOwn" class="message-status">
          ✓ 已送達
        </span>
      </div>
    </div>

    <!-- 空白佔位 (避免頭像影響排版) -->
    <div v-if="isOwn" class="message-spacer"></div>
  </div>
</template>

<script setup>
import { ref, computed, h } from 'vue'
import { NAvatar, NDropdown, NIcon } from 'naive-ui'
import { TrashOutline } from '@vicons/ionicons5'

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  isOwn: {
    type: Boolean,
    default: false
  },
  showAvatar: {
    type: Boolean,
    default: true
  },
  otherUserAvatar: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['delete', 'preview-image'])

const defaultAvatar = '/default-avatar.svg'
const showDropdown = ref(false)

// 判斷訊息類型
const isTextMessage = computed(() => {
  return !props.message.message_type || props.message.message_type === 'TEXT'
})

const isImageMessage = computed(() => {
  return ['IMAGE', 'GIF'].includes(props.message.message_type)
})

const isGif = computed(() => {
  return props.message.message_type === 'GIF'
})

// 解析圖片內容
const imageContent = computed(() => {
  if (!isImageMessage.value) return null
  try {
    return JSON.parse(props.message.content)
  } catch {
    // 如果解析失敗，假設 content 本身就是 URL
    return {
      image_url: props.message.content,
      thumbnail_url: props.message.content
    }
  }
})

// 右鍵選單選項
const dropdownOptions = [
  {
    label: '刪除訊息',
    key: 'delete',
    icon: () => h(NIcon, null, { default: () => h(TrashOutline) })
  }
]

// 處理右鍵點擊
const handleContextMenu = (e) => {
  e.preventDefault()
  showDropdown.value = true
}

// 處理選單選擇
const handleDropdownSelect = (key) => {
  if (key === 'delete') {
    emit('delete', props.message.id)
  }
  showDropdown.value = false
}

// 處理圖片點擊（放大查看）
const handleImageClick = () => {
  if (imageContent.value) {
    emit('preview-image', imageContent.value.image_url)
  }
}

// 格式化時間
const formattedTime = computed(() => {
  if (!props.message.sent_at) return ''

  const date = new Date(props.message.sent_at)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '剛剛'
  if (diffMins < 60) return `${diffMins} 分鐘前`
  if (diffHours < 24) return `${diffHours} 小時前`
  if (diffDays < 7) return `${diffDays} 天前`

  return date.toLocaleDateString('zh-TW', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
})
</script>

<style scoped>
.message-bubble {
  display: flex;
  align-items: flex-end;
  margin-bottom: 12px;
  gap: 8px;
}

.message-own {
  flex-direction: row-reverse;
}

.message-other {
  flex-direction: row;
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
}

.message-content-wrapper {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-own .message-content-wrapper {
  align-items: flex-end;
}

.message-other .message-content-wrapper {
  align-items: flex-start;
}

.message-content {
  padding: 10px 14px;
  border-radius: 18px;
  word-wrap: break-word;
  word-break: break-word;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.5;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  cursor: context-menu;
  user-select: text;
}

.message-own .message-content {
  border-bottom-right-radius: 4px;
}

.message-other .message-content {
  border-bottom-left-radius: 4px;
}

/* 圖片訊息樣式 */
.message-image {
  position: relative;
  max-width: 250px;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s ease;
}

.message-image:hover {
  transform: scale(1.02);
}

.message-image img {
  width: 100%;
  display: block;
  background-color: #f5f5f5;
}

.gif-badge {
  position: absolute;
  bottom: 8px;
  left: 8px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.message-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #999;
  padding: 0 4px;
}

.message-time {
  white-space: nowrap;
}

.message-status {
  color: #1890ff;
  white-space: nowrap;
}

.message-spacer {
  flex-shrink: 0;
  width: 32px;
}
</style>
