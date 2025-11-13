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
      <!-- 訊息氣泡 -->
      <div
        :class="[
          'message-content',
          isOwn ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-900'
        ]"
      >
        {{ message.content }}
      </div>

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
import { computed } from 'vue'
import { NAvatar } from 'naive-ui'

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

const defaultAvatar = 'https://via.placeholder.com/40'

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
}

.message-own .message-content {
  border-bottom-right-radius: 4px;
}

.message-other .message-content {
  border-bottom-left-radius: 4px;
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
