<template>
  <div class="interest-selector">
    <h3>興趣標籤</h3>
    <p class="hint">
      選擇 3-10 個興趣標籤 (已選擇: {{ selectedCount }}/10)
      <span v-if="selectedCount < 3" class="warning">⚠️ 至少選擇 3 個</span>
      <span v-else-if="selectedCount >= 3 && selectedCount <= 10" class="success">✅</span>
    </p>

    <!-- 分類標籤 -->
    <div v-if="Object.keys(tagsByCategory).length > 0" class="categories">
      <div
        v-for="(tags, category) in tagsByCategory"
        :key="category"
        class="category-section"
      >
        <h4 class="category-title">{{ getCategoryName(category) }}</h4>
        <div class="tags-grid">
          <button
            v-for="tag in tags"
            :key="tag.id"
            class="tag-button"
            :class="{ selected: isSelected(tag.id) }"
            @click="toggleTag(tag.id)"
            :disabled="!isSelected(tag.id) && selectedCount >= 10"
          >
            <span class="tag-icon">{{ tag.icon }}</span>
            <span class="tag-name">{{ tag.name }}</span>
            <span v-if="isSelected(tag.id)" class="tag-check">✓</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 載入中 -->
    <div v-else-if="profileStore.loading" class="loading">
      <div class="spinner-small"></div>
      <p>載入標籤中...</p>
    </div>

    <!-- 無資料 -->
    <div v-else class="empty-state">
      <p>目前沒有可用的興趣標籤</p>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useProfileStore } from '@/stores/profile'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const profileStore = useProfileStore()

// 已選擇的標籤數量
const selectedCount = computed(() => props.modelValue.length)

// 依分類分組的標籤
const tagsByCategory = computed(() => profileStore.getTagsByCategory)

/**
 * 取得分類名稱
 */
const getCategoryName = (category) => {
  const names = {
    sports: '🏃 運動',
    music: '🎵 音樂',
    food: '🍽️ 美食',
    travel: '✈️ 旅遊',
    art: '🎨 藝術',
    reading: '📚 閱讀',
    tech: '💻 科技',
    pets: '🐾 寵物',
    entertainment: '🎬 影視娛樂',
    others: '✨ 其他'
  }
  return names[category] || category
}

/**
 * 檢查是否已選擇
 */
const isSelected = (tagId) => {
  return props.modelValue.includes(tagId)
}

/**
 * 切換標籤選擇狀態
 */
const toggleTag = (tagId) => {
  const selected = [...props.modelValue]

  if (isSelected(tagId)) {
    // 取消選擇
    const index = selected.indexOf(tagId)
    selected.splice(index, 1)
  } else {
    // 選擇（最多 10 個）
    if (selected.length < 10) {
      selected.push(tagId)
    }
  }

  emit('update:modelValue', selected)
}
</script>

<style scoped>
.interest-selector {
  margin: 1.5rem 0;
}

.interest-selector h3 {
  margin-bottom: 0.5rem;
  color: #333;
}

.hint {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.hint .warning {
  color: #f39c12;
  font-weight: 600;
  margin-left: 0.5rem;
}

.hint .success {
  color: #27ae60;
  font-weight: 600;
  margin-left: 0.5rem;
}

.categories {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.category-section {
  margin-bottom: 1rem;
}

.category-title {
  margin-bottom: 1rem;
  color: #555;
  font-size: 1.1rem;
  font-weight: 600;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #f0f0f0;
}

.tags-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
}

.tag-button {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  min-height: 80px;
}

.tag-button:hover:not(:disabled) {
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.tag-button.selected {
  border-color: #667eea;
  background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
}

.tag-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tag-icon {
  font-size: 1.8rem;
}

.tag-name {
  font-size: 0.9rem;
  color: #333;
  text-align: center;
}

.tag-check {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 20px;
  height: 20px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  color: #666;
}

.spinner-small {
  width: 30px;
  height: 30px;
  border: 3px solid #e0e0e0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #999;
}

@media (max-width: 768px) {
  .tags-grid {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  }

  .tag-button {
    min-height: 70px;
    padding: 0.75rem;
  }

  .tag-icon {
    font-size: 1.5rem;
  }

  .tag-name {
    font-size: 0.85rem;
  }
}
</style>
