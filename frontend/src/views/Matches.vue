<template>
  <div class="matches">
    <div class="container">
      <h1 class="page-title">我的配對</h1>

      <!-- 載入中 -->
      <div v-if="discoveryStore.loading && discoveryStore.matches.length === 0" class="loading">
        <div class="spinner"></div>
        <p>載入中...</p>
      </div>

      <!-- 錯誤訊息 -->
      <div v-else-if="discoveryStore.error" class="error-message">
        <p>❌ {{ discoveryStore.error }}</p>
        <button @click="loadMatches" class="btn-retry">重試</button>
      </div>

      <!-- 空狀態 -->
      <div v-else-if="!discoveryStore.hasMatches" class="empty-state">
        <div class="empty-icon">💔</div>
        <h2>還沒有配對</h2>
        <p>開始探索並喜歡其他用戶來建立配對！</p>
        <router-link to="/discovery" class="btn-discover">
          <span class="btn-icon">🔍</span>
          <span>開始探索</span>
        </router-link>
      </div>

      <!-- 配對列表 -->
      <div v-else class="matches-grid">
        <div
          v-for="match in discoveryStore.matches"
          :key="match.match_id"
          class="match-card"
        >
          <!-- 用戶頭像 -->
          <div class="match-avatar">
            <img
              v-if="match.profile_picture"
              :src="match.profile_picture"
              :alt="match.display_name"
            >
            <div v-else class="avatar-placeholder">
              {{ match.display_name[0] }}
            </div>
            <div class="online-status" :class="{ online: isOnline(match.last_active) }"></div>
          </div>

          <!-- 用戶資訊 -->
          <div class="match-info">
            <div class="match-header">
              <h3 class="match-name">{{ match.display_name }}</h3>
              <span class="match-age">{{ match.age }}</span>
            </div>

            <p v-if="match.distance_km" class="match-distance">
              📍 {{ formatDistance(match.distance_km) }}
            </p>

            <p class="match-date">
              配對於 {{ formatDate(match.matched_at) }}
            </p>

            <!-- 共同興趣 -->
            <div v-if="match.interests && match.interests.length > 0" class="match-interests">
              <span
                v-for="interest in match.interests.slice(0, 3)"
                :key="interest"
                class="interest-tag"
              >
                {{ interest }}
              </span>
            </div>
          </div>

          <!-- 操作按鈕 -->
          <div class="match-actions">
            <button
              @click="showUnmatchConfirm(match)"
              class="btn-unmatch"
              title="取消配對"
            >
              💔
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 取消配對確認彈窗 -->
    <Transition name="modal">
      <div v-if="unmatchTarget" class="modal-overlay" @click="cancelUnmatch">
        <div class="modal-container" @click.stop>
          <div class="modal-content">
            <div class="modal-icon">⚠️</div>
            <h2 class="modal-title">確定要取消配對？</h2>
            <p class="modal-subtitle">
              此操作無法復原，您將不再能與 {{ unmatchTarget.display_name }} 聊天。
            </p>
            <div class="modal-actions">
              <button @click="cancelUnmatch" class="btn-cancel">
                取消
              </button>
              <button @click="confirmUnmatch" class="btn-confirm" :disabled="isUnmatching">
                {{ isUnmatching ? '處理中...' : '確定取消' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDiscoveryStore } from '@/stores/discovery'

const discoveryStore = useDiscoveryStore()

const unmatchTarget = ref(null)
const isUnmatching = ref(false)

/**
 * 格式化距離顯示
 */
const formatDistance = (km) => {
  if (km < 1) {
    return `${Math.round(km * 1000)}m`
  } else if (km < 10) {
    return `${km.toFixed(1)}km`
  } else {
    return `${Math.round(km)}km`
  }
}

/**
 * 格式化日期顯示
 */
const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffInMs = now - date
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))

  if (diffInDays === 0) {
    return '今天'
  } else if (diffInDays === 1) {
    return '昨天'
  } else if (diffInDays < 7) {
    return `${diffInDays} 天前`
  } else if (diffInDays < 30) {
    const weeks = Math.floor(diffInDays / 7)
    return `${weeks} 週前`
  } else {
    return date.toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }
}

/**
 * 判斷是否在線（最近 5 分鐘活躍）
 */
const isOnline = (lastActive) => {
  if (!lastActive) return false
  const lastActiveDate = new Date(lastActive)
  const now = new Date()
  const diffInMinutes = (now - lastActiveDate) / (1000 * 60)
  return diffInMinutes < 5
}

/**
 * 載入配對列表
 */
const loadMatches = async () => {
  try {
    await discoveryStore.fetchMatches()
  } catch (error) {
    console.error('載入配對列表失敗:', error)
  }
}

/**
 * 顯示取消配對確認彈窗
 */
const showUnmatchConfirm = (match) => {
  unmatchTarget.value = match
}

/**
 * 取消取消配對操作
 */
const cancelUnmatch = () => {
  unmatchTarget.value = null
}

/**
 * 確認取消配對
 */
const confirmUnmatch = async () => {
  if (!unmatchTarget.value || isUnmatching.value) return

  isUnmatching.value = true

  try {
    await discoveryStore.unmatch(unmatchTarget.value.match_id)
    unmatchTarget.value = null
  } catch (error) {
    console.error('取消配對失敗:', error)
  } finally {
    isUnmatching.value = false
  }
}

onMounted(() => {
  loadMatches()
})
</script>

<style scoped>
.matches {
  min-height: 100vh;
  background: linear-gradient(135deg, #FFF5F5 0%, #FFE5E5 100%);
  padding: 20px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  text-align: center;
  font-size: 32px;
  font-weight: 700;
  color: #333;
  margin-bottom: 30px;
}

/* 載入中 */
.loading {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 50px;
  height: 50px;
  margin: 0 auto 20px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #FF6B6B;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 錯誤訊息 */
.error-message {
  text-align: center;
  padding: 40px 20px;
}

.error-message p {
  color: #e74c3c;
  font-size: 16px;
  margin-bottom: 20px;
}

.btn-retry {
  padding: 12px 30px;
  background: #FF6B6B;
  color: white;
  border: none;
  border-radius: 25px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-retry:hover {
  background: #FF5252;
  transform: translateY(-2px);
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.empty-state h2 {
  font-size: 24px;
  color: #333;
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 16px;
  color: #666;
  margin-bottom: 30px;
}

.btn-discover {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 30px;
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
  color: white;
  text-decoration: none;
  border-radius: 25px;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.btn-discover:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

.btn-icon {
  font-size: 20px;
}

/* 配對網格 */
.matches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

/* 配對卡片 */
.match-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.match-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

/* 用戶頭像 */
.match-avatar {
  position: relative;
  flex-shrink: 0;
}

.match-avatar img,
.avatar-placeholder {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
  color: white;
  font-size: 32px;
  font-weight: bold;
}

.online-status {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ccc;
  border: 3px solid white;
}

.online-status.online {
  background: #4CAF50;
  box-shadow: 0 0 8px rgba(76, 175, 80, 0.6);
}

/* 用戶資訊 */
.match-info {
  flex: 1;
  min-width: 0;
}

.match-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.match-name {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.match-age {
  font-size: 18px;
  color: #666;
  flex-shrink: 0;
}

.match-distance {
  font-size: 13px;
  color: #999;
  margin: 0 0 6px;
}

.match-date {
  font-size: 12px;
  color: #999;
  margin: 0 0 12px;
}

.match-interests {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.interest-tag {
  display: inline-block;
  padding: 4px 10px;
  background: #FFF0F0;
  color: #FF6B6B;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

/* 操作按鈕 */
.match-actions {
  flex-shrink: 0;
}

.btn-unmatch {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: #f5f5f5;
  font-size: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-unmatch:hover {
  background: #FFE5E5;
  transform: scale(1.1);
}

/* Modal 覆蓋層 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

/* Modal 容器 */
.modal-container {
  background: white;
  border-radius: 20px;
  max-width: 450px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* Modal 內容 */
.modal-content {
  padding: 40px 30px 30px;
  text-align: center;
}

.modal-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.modal-title {
  font-size: 24px;
  font-weight: 700;
  color: #333;
  margin: 0 0 12px;
}

.modal-subtitle {
  font-size: 15px;
  color: #666;
  line-height: 1.5;
  margin: 0 0 30px;
}

.modal-actions {
  display: flex;
  gap: 12px;
}

.modal-actions button {
  flex: 1;
  padding: 14px 20px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-cancel {
  background: #f5f5f5;
  color: #666;
}

.btn-cancel:hover {
  background: #e0e0e0;
}

.btn-confirm {
  background: #e74c3c;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background: #c0392b;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal 過渡效果 */
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from, .modal-leave-to {
  opacity: 0;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .matches-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .match-card {
    padding: 16px;
  }

  .match-avatar img,
  .avatar-placeholder {
    width: 60px;
    height: 60px;
  }

  .avatar-placeholder {
    font-size: 24px;
  }

  .match-name {
    font-size: 18px;
  }
}
</style>
