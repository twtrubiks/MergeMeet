<template>
  <div class="matches">
    <div class="container">
      <!-- 返回主選單按鈕 -->
      <router-link to="/" class="back-home-btn" aria-label="返回主選單">
        <Icon name="home" size="sm" decorative class="btn-icon" />
        <span class="btn-text">返回主選單</span>
      </router-link>

      <h1 class="page-title">
        <Icon name="heart" size="lg" decorative class="title-heart-icon" />
        我的配對
      </h1>

      <!-- 載入中 - 使用 Skeleton Loader -->
      <div
        v-if="discoveryStore.loading && discoveryStore.matches.length === 0"
        class="loading-skeleton"
      >
        <div class="matches-grid">
          <SkeletonCard v-for="i in 4" :key="i" />
        </div>
      </div>

      <!-- 錯誤訊息 -->
      <div v-else-if="discoveryStore.error" class="error-message" role="alert">
        <div class="error-icon" aria-hidden="true">
          <Icon name="alert-outline" size="xl" decorative />
        </div>
        <p>{{ discoveryStore.error }}</p>
        <AnimatedButton variant="danger" @click="loadMatches">
          <Icon name="refresh" size="sm" decorative />
          重試
        </AnimatedButton>
      </div>

      <!-- 空狀態 -->
      <div v-else-if="!discoveryStore.hasMatches" class="empty-state">
        <div class="empty-animation" aria-hidden="true">
          <div class="broken-heart">
            <Icon name="heart-dislike" size="xl" decorative class="broken-heart-icon" />
          </div>
        </div>
        <h2>還沒有配對</h2>
        <p>開始探索並喜歡其他用戶來建立配對！</p>
        <AnimatedButton variant="primary" @click="$router.push('/discovery')">
          <Icon name="search" size="sm" decorative />
          開始探索
        </AnimatedButton>
      </div>

      <!-- 配對列表 -->
      <div v-else>
        <div class="matches-stats">
          <Badge variant="success" size="large"> {{ discoveryStore.matches.length }} 個配對 </Badge>
        </div>

        <div class="matches-grid">
          <div
            v-for="(match, index) in discoveryStore.matches"
            :key="match.match_id"
            class="match-card"
            :style="{ animationDelay: `${index * 0.1}s` }"
          >
            <!-- 新配對標籤 -->
            <div v-if="isNewMatch(match.matched_at)" class="new-match-badge">
              <Icon name="flash" size="sm" decorative /> NEW
            </div>

            <!-- 用戶頭像（可點擊查看詳情） -->
            <div class="match-avatar clickable" @click="openUserDetail(match)">
              <div
                class="avatar-ring"
                :class="{ online: isOnline(match.matched_user.last_active) }"
              >
                <img
                  v-if="match.matched_user.photos && match.matched_user.photos.length > 0"
                  :src="match.matched_user.photos[0]"
                  :alt="match.matched_user.display_name"
                />
                <div v-else class="avatar-placeholder">
                  {{ (match.matched_user.display_name || 'U')[0] }}
                </div>
              </div>
              <div v-if="isOnline(match.matched_user.last_active)" class="online-pulse"></div>
            </div>

            <!-- 用戶資訊（可點擊查看詳情） -->
            <div class="match-info clickable" @click="openUserDetail(match)">
              <div class="match-header">
                <h3 class="match-name">{{ match.matched_user.display_name }}</h3>
                <span class="match-age">{{ match.matched_user.age }}</span>
              </div>

              <p v-if="match.matched_user.distance_km != null" class="match-distance">
                <Icon name="location" size="xs" decorative />
                {{ formatDistance(match.matched_user.distance_km) }}
              </p>

              <div class="match-meta">
                <Badge variant="info" size="small">
                  {{ formatDate(match.matched_at) }}
                </Badge>
                <Badge
                  v-if="isOnline(match.matched_user.last_active)"
                  variant="success"
                  size="small"
                >
                  ● 在線
                </Badge>
              </div>

              <!-- 興趣標籤（共同興趣排前並高亮，作為配對理由） -->
              <div
                v-if="match.matched_user.interests && match.matched_user.interests.length > 0"
                class="match-interests"
              >
                <span
                  v-for="tag in displayInterests(match.matched_user, MAX_MATCH_INTERESTS)"
                  :key="tag.name"
                  class="interest-tag"
                  :class="{ 'interest-tag--common': tag.common }"
                >
                  <template v-if="tag.common">
                    <Icon name="heart" size="xs" decorative />
                    <span class="sr-only">共同興趣：</span>
                  </template>
                  {{ tag.name }}
                </span>
                <span
                  v-if="match.matched_user.interests.length > MAX_MATCH_INTERESTS"
                  class="interest-more"
                >
                  +{{ match.matched_user.interests.length - MAX_MATCH_INTERESTS }}
                </span>
              </div>
            </div>

            <!-- 操作按鈕 -->
            <div class="match-actions">
              <button
                class="btn-chat"
                title="開始聊天"
                aria-label="與該用戶開始聊天對話"
                :aria-describedby="`chat-desc-${match.match_id}`"
                @click="openChat(match.match_id)"
              >
                <Icon name="chat" size="md" decorative />
                <span :id="`chat-desc-${match.match_id}`" class="sr-only"
                  >點擊後將開啟與 {{ match.matched_user.display_name }} 的聊天視窗</span
                >
              </button>
              <button
                class="btn-unmatch"
                title="取消配對"
                aria-label="取消與該用戶的配對關係"
                :aria-describedby="`unmatch-desc-${match.match_id}`"
                @click="showUnmatchConfirm(match)"
              >
                <Icon name="heart-dislike" size="md" decorative />
                <span :id="`unmatch-desc-${match.match_id}`" class="sr-only"
                  >點擊後將取消與 {{ match.matched_user.display_name }} 的配對</span
                >
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 用戶詳情彈窗 -->
    <UserDetailModal :show="showUserDetail" :user="selectedUser || {}" @close="closeUserDetail" />

    <!-- 取消配對確認彈窗 -->
    <Transition name="modal">
      <div
        v-if="unmatchTarget"
        class="modal-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="unmatch-dialog-title"
        aria-describedby="unmatch-dialog-desc"
        @click="cancelUnmatch"
      >
        <div class="modal-container" @click.stop>
          <div class="modal-content">
            <div class="modal-icon" aria-hidden="true">
              <Icon name="alert-outline" size="xl" decorative class="modal-alert-icon" />
            </div>
            <h2 id="unmatch-dialog-title" class="modal-title">確定要取消配對？</h2>
            <p id="unmatch-dialog-desc" class="modal-subtitle">
              此操作無法復原，您將不再能與 {{ unmatchTarget.matched_user.display_name }} 聊天。
            </p>
            <div class="modal-actions">
              <AnimatedButton
                variant="ghost"
                aria-label="取消此操作，返回配對列表"
                @click="cancelUnmatch"
              >
                取消
              </AnimatedButton>
              <AnimatedButton
                variant="danger"
                :loading="isUnmatching"
                aria-label="確認取消配對"
                :aria-busy="isUnmatching"
                @click="confirmUnmatch"
              >
                <span v-if="!isUnmatching">確定取消</span>
              </AnimatedButton>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useDiscoveryStore } from '@/stores/discovery'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import Badge from '@/components/ui/Badge.vue'
import UserDetailModal from '@/components/UserDetailModal.vue'
import Icon from '@/components/ui/Icon.vue'
import { formatMatchDate } from '@/utils/dateFormat'
import { displayInterests } from '@/utils/interests'
import { formatDistance } from '@/utils/distance'
import { logger } from '@/utils/logger'

// 配對卡片最多顯示的興趣數
const MAX_MATCH_INTERESTS = 3

const router = useRouter()
const discoveryStore = useDiscoveryStore()
const message = useMessage()

const unmatchTarget = ref(null)
const isUnmatching = ref(false)

// 用戶詳情 Modal 狀態
const showUserDetail = ref(false)
const selectedUser = ref(null)

/**
 * 開啟用戶詳情 Modal
 */
const openUserDetail = (match) => {
  selectedUser.value = match.matched_user
  showUserDetail.value = true
}

/**
 * 關閉用戶詳情 Modal
 */
const closeUserDetail = () => {
  showUserDetail.value = false
  selectedUser.value = null
}

/**
 * 格式化日期顯示
 * 使用共享的工具函數
 */
const formatDate = formatMatchDate

/**
 * 判斷是否為新配對（24小時內）
 */
const isNewMatch = (matchedAt) => {
  const matchDate = new Date(matchedAt)
  const now = new Date()
  const diffInHours = (now - matchDate) / (1000 * 60 * 60)
  return diffInHours < 24
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
    logger.error('載入配對列表失敗:', error)
  }
}

/**
 * 開啟聊天室
 */
const openChat = (matchId) => {
  router.push(`/messages/${matchId}`)
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
    // 成功後才關閉彈窗和清空目標
    unmatchTarget.value = null
    message.success('已取消配對')
  } catch (error) {
    logger.error('取消配對失敗:', error)
    // 顯示用戶友好的錯誤訊息
    message.error('取消配對失敗,請稍後再試')
    // 保持彈窗打開,讓用戶可以重試
  } finally {
    isUnmatching.value = false
  }
}

/**
 * ESC 鍵關閉 Modal (鍵盤導航支持)
 */
const handleEscKey = (event) => {
  if (event.key === 'Escape' && unmatchTarget.value) {
    cancelUnmatch()
  }
}

onMounted(() => {
  loadMatches()
  // 添加鍵盤事件監聽器
  window.addEventListener('keydown', handleEscKey)
})

onUnmounted(() => {
  // 清理鍵盤事件監聽器
  window.removeEventListener('keydown', handleEscKey)
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

.matches {
  min-height: 100vh;
  background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%);
  padding: 20px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

/* 返回主選單按鈕 */
.back-home-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  background: rgba(255, 255, 255, 0.95);
  color: var(--color-like-accessible);
  text-decoration: none;
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
  box-shadow: var(--shadow-button);
  transition: all var(--duration-slow) var(--easing-default);
  margin-bottom: var(--space-4);
}

.back-home-btn:hover {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--color-like-alpha-20);
}

.back-home-btn .btn-icon {
  display: inline-flex;
}

.back-home-btn .btn-text {
  font-size: var(--font-size-sm);
}

.page-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  text-align: center;
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-extrabold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-8);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 標題愛心圖標 */
.title-heart-icon {
  color: var(--color-like);
}

/* 載入中 - Skeleton */
.loading-skeleton {
  padding: var(--space-5) 0;
}

/* 錯誤訊息 */
.error-message {
  text-align: center;
  padding: var(--space-16) var(--space-5);
}

.error-icon {
  color: var(--color-error-500);
  margin-bottom: var(--space-4);
}

.error-message p {
  color: var(--color-error-600);
  font-size: var(--font-size-lg);
  margin-bottom: var(--space-6);
  font-weight: var(--font-weight-semibold);
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  animation: fadeIn 0.6s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.empty-animation {
  margin-bottom: 32px;
}

.broken-heart {
  display: inline-flex;
  color: var(--color-like);
  animation: heartbreak 2s ease-in-out infinite;
}

/* 放大空狀態心碎圖標 */
.broken-heart-icon {
  transform: scale(2.5); /* 120px / 48px = 2.5 */
}

@keyframes heartbreak {
  0%,
  100% {
    transform: rotate(0deg) scale(1);
  }
  25% {
    transform: rotate(-10deg) scale(1.1);
  }
  75% {
    transform: rotate(10deg) scale(1.1);
  }
}

.empty-state h2 {
  font-size: 2rem;
  color: var(--color-text-primary);
  margin-bottom: 16px;
  font-weight: 700;
}

.empty-state p {
  font-size: 1.1rem;
  color: var(--color-text-muted);
  margin-bottom: 32px;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

/* 配對統計 */
.matches-stats {
  display: flex;
  justify-content: center;
  margin-bottom: 32px;
}

/* 配對網格 */
.matches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 24px;
}

/* 配對卡片 */
.match-card {
  position: relative;
  background: white;
  border-radius: var(--radius-xl);
  padding: 24px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  gap: 20px;
  align-items: flex-start;
  border: 2px solid transparent;
  animation: slideIn 0.5s ease-out both;
  overflow: hidden;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.match-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 107, 107, 0.1), transparent);
  transition: left 0.5s;
}

.match-card:hover::before {
  left: 100%;
}

.match-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 30px rgba(255, 107, 107, 0.15);
  border-color: rgba(255, 107, 107, 0.3);
}

/* 新配對標籤 */
.new-match-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  background: linear-gradient(135deg, #ffd700, #ffa500);
  color: white;
  padding: 6px 12px;
  border-radius: var(--radius-xl);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 8px rgba(255, 215, 0, 0.4);
  animation: glow 2s ease-in-out infinite;
  z-index: 1;
}

@keyframes glow {
  0%,
  100% {
    box-shadow: 0 2px 8px rgba(255, 215, 0, 0.4);
  }
  50% {
    box-shadow: 0 4px 16px rgba(255, 215, 0, 0.6);
  }
}

/* 可點擊區域 */
.clickable {
  cursor: pointer;
  transition: opacity 0.2s;
}

.clickable:hover {
  opacity: 0.85;
}

/* 用戶頭像 */
.match-avatar {
  position: relative;
  flex-shrink: 0;
}

.avatar-ring {
  position: relative;
  padding: 4px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-background-light), var(--color-border));
  transition: all 0.3s ease;
}

.avatar-ring.online {
  background: linear-gradient(135deg, #4caf50, #66bb6a);
}

.avatar-ring img,
.avatar-placeholder {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid white;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff6b6b, #ff8e53);
  color: white;
  font-size: var(--font-size-4xl);
  font-weight: 800;
}

.online-pulse {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  background: var(--color-success-500);
  border-radius: 50%;
  border: 3px solid white;
  box-shadow: 0 0 0 rgba(76, 175, 80, 0.7);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(76, 175, 80, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
  }
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
  font-size: 1.4rem;
  font-weight: 800;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background: var(--color-primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.match-age {
  font-size: 1.2rem;
  color: var(--color-text-muted);
  font-weight: 600;
  flex-shrink: 0;
}

.match-distance {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-2);
  font-weight: var(--font-weight-medium);
}

.match-meta {
  display: flex;
  gap: 8px;
  margin: 10px 0;
  flex-wrap: wrap;
}

.match-interests {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.interest-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  background: linear-gradient(135deg, var(--color-primary-alpha-10), var(--color-primary-alpha-10));
  color: var(--color-primary-500);
  border: 1px solid var(--color-primary-alpha-30);
  border-radius: var(--radius-lg);
  font-size: 0.8rem;
  font-weight: 600;
  transition: all 0.2s ease;
}

/* 共同興趣：實色主色底 + 白字（對比 ≈ 4.9:1，符合 WCAG AA 小字） */
.interest-tag--common {
  gap: var(--space-1);
  background: var(--color-primary-600);
  color: #fff;
  border-color: var(--color-primary-600);
}

.interest-tag:hover {
  transform: scale(1.05);
  background: linear-gradient(135deg, rgba(225, 29, 72, 0.15), rgba(225, 29, 72, 0.15));
}

/* 覆蓋 .interest-tag:hover 的淡色底（同特異性，必須排在其後） */
.interest-tag--common:hover {
  background: var(--color-primary-600);
}

.interest-more {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-text-muted);
  border-radius: var(--radius-lg);
  font-size: 0.8rem;
  font-weight: 600;
}

/* 操作按鈕 */
.match-actions {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-chat,
.btn-unmatch {
  position: relative;
  width: 50px;
  height: 50px;
  border: none;
  border-radius: 50%;
  font-size: 1.3rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.btn-chat {
  background: linear-gradient(135deg, #38bdf8, #0ea5e9);
}

.btn-unmatch {
  background: linear-gradient(135deg, #f093fb, #f5576c);
}

.btn-chat::before,
.btn-unmatch::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition:
    width 0.4s,
    height 0.4s;
}

.btn-chat:hover::before,
.btn-unmatch:hover::before {
  width: 100%;
  height: 100%;
}

.btn-chat:hover {
  transform: scale(1.15) translateY(-3px);
  box-shadow: 0 8px 20px rgba(56, 189, 248, 0.4);
}

.btn-unmatch:hover {
  transform: scale(1.15) translateY(-3px);
  box-shadow: 0 8px 20px rgba(245, 87, 108, 0.4);
}

.btn-chat:active,
.btn-unmatch:active {
  transform: scale(1.05);
}

/* Modal 覆蓋層 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

/* Modal 容器 */
.modal-container {
  background: white;
  border-radius: var(--radius-2xl);
  max-width: 480px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: modalSlideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border: 2px solid rgba(255, 255, 255, 0.8);
}

@keyframes modalSlideUp {
  from {
    transform: translateY(60px) scale(0.95);
    opacity: 0;
  }
  to {
    transform: translateY(0) scale(1);
    opacity: 1;
  }
}

/* Modal 內容 */
.modal-content {
  padding: 48px 32px 32px;
  text-align: center;
}

.modal-icon {
  color: var(--color-warning-500);
  margin-bottom: var(--space-6);
  animation: iconBounce 0.6s ease-out;
}

/* 放大彈窗警告圖標 */
.modal-alert-icon {
  transform: scale(1.33); /* 64px / 48px ≈ 1.33 */
}

@keyframes iconBounce {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.modal-title {
  font-size: 1.8rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--color-text-primary), var(--color-text-muted));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 16px;
}

.modal-subtitle {
  font-size: 1.05rem;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin: 0 0 32px;
  font-weight: 500;
}

.modal-actions {
  display: flex;
  gap: 16px;
}

/* Modal 過渡效果 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .page-title {
    font-size: 2rem;
  }

  .matches-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .match-card {
    padding: 20px;
    gap: 16px;
  }

  .avatar-ring img,
  .avatar-placeholder {
    width: 70px;
    height: 70px;
  }

  .avatar-placeholder {
    font-size: 28px;
  }

  .match-name {
    font-size: 1.2rem;
  }

  .match-age {
    font-size: 1rem;
  }

  .btn-chat,
  .btn-unmatch {
    width: 45px;
    height: 45px;
    font-size: 1.1rem;
  }

  .modal-container {
    margin: 0 16px;
  }

  .modal-content {
    padding: 36px 24px 24px;
  }

  .modal-icon {
    font-size: 4rem;
  }

  .modal-title {
    font-size: 1.5rem;
  }

  .modal-subtitle {
    font-size: 0.95rem;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.75rem;
  }

  .match-card {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .match-avatar {
    margin-bottom: 12px;
  }

  .match-info {
    width: 100%;
  }

  .match-header {
    justify-content: center;
  }

  .match-actions {
    flex-direction: row;
    width: 100%;
    justify-content: center;
    margin-top: 16px;
  }

  .match-interests {
    justify-content: center;
  }

  .new-match-badge {
    top: 8px;
    left: 8px;
    font-size: 0.65rem;
    padding: 4px 10px;
  }
}
</style>
