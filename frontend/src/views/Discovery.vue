<template>
  <div class="discovery">
    <div class="container">
      <!-- 返回主選單按鈕 -->
      <router-link to="/" class="back-home-btn" aria-label="返回主選單">
        <Icon name="home" size="sm" decorative class="btn-icon" />
        <span class="btn-text">返回主選單</span>
      </router-link>

      <h1 class="page-title">探索配對</h1>

      <!-- 載入中 -->
      <div
        v-if="discoveryStore.loading && !discoveryStore.currentCandidate"
        class="loading"
        aria-busy="true"
      >
        <HeartLoader text="正在為你探索附近的人..." />
      </div>

      <!-- 錯誤訊息 -->
      <ErrorState
        v-else-if="discoveryStore.error"
        title="無法載入候選人"
        :message="discoveryStore.error"
        @retry="loadCandidates"
      />

      <!-- 沒有候選人 -->
      <div v-else-if="!discoveryStore.hasCandidates" class="empty-state">
        <div class="empty-icon" aria-hidden="true">
          <Icon name="search" size="xl" decorative class="empty-search-icon" />
        </div>
        <h2>沒有更多候選人了</h2>
        <p>請稍後再回來查看</p>
        <button class="btn-refresh" @click="loadCandidates">重新整理</button>
      </div>

      <!-- 卡片堆疊區域 -->
      <div v-else class="cards-container" role="application" :aria-label="currentCandidateAria">
        <!-- 候選人卡片 -->
        <div
          v-for="(candidate, index) in visibleCandidates"
          :key="candidate.user_id"
          class="candidate-card"
          :class="{
            'top-card': index === 0,
            'exit-right': index === 0 && exitDirection === 'right',
            'exit-left': index === 0 && exitDirection === 'left'
          }"
        >
          <!-- 照片 -->
          <div class="card-image">
            <img
              v-if="candidate.photos?.length"
              :src="candidate.photos[0]"
              :alt="candidate.display_name"
              loading="lazy"
              @error="(e) => (e.target.src = defaultAvatar)"
            />
            <div v-else class="image-placeholder">
              <span>{{ candidate.display_name[0] }}</span>
            </div>

            <!-- 配對分數標籤 -->
            <div class="match-score">
              <Icon name="heart" size="sm" decorative class="score-icon" />
              <span class="score-value">{{ candidate.match_score }}%</span>
            </div>

            <!-- 舉報按鈕 -->
            <button
              v-if="index === 0"
              class="report-btn"
              title="舉報此用戶"
              aria-label="舉報此用戶"
              @click.stop="handleOpenReportModal(candidate)"
            >
              <Icon name="alert-outline" size="sm" decorative />
            </button>
          </div>

          <!-- 卡片資訊 -->
          <div
            class="card-info"
            :role="index === 0 ? 'button' : undefined"
            :tabindex="index === 0 ? 0 : undefined"
            :aria-label="index === 0 ? `查看 ${candidate.display_name} 的完整資料` : undefined"
            @click.stop="index === 0 ? openUserDetail(candidate) : null"
            @keydown.enter.stop="index === 0 ? openUserDetail(candidate) : null"
          >
            <div class="card-header">
              <h2 class="card-name">{{ candidate.display_name }}</h2>
              <span class="card-age">{{ candidate.age }}</span>
            </div>

            <!-- 距離 -->
            <p v-if="candidate.distance_km" class="card-distance">
              <Icon name="location" size="xs" decorative class="distance-icon" />
              {{ formatDistance(candidate.distance_km) }}
            </p>

            <!-- 興趣標籤 -->
            <div
              v-if="candidate.interests && candidate.interests.length > 0"
              class="card-interests"
            >
              <span
                v-for="interest in candidate.interests.slice(0, 5)"
                :key="interest"
                class="interest-tag"
              >
                {{ interest }}
              </span>
            </div>

            <!-- 自我介紹 -->
            <p v-if="candidate.bio" class="card-bio">{{ candidate.bio }}</p>

            <!-- 點擊查看詳情提示 -->
            <div v-if="index === 0" class="view-detail-hint">
              <span><Icon name="hand" size="xs" decorative /> 點擊查看完整資料</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 螢幕閱讀器播報區域 -->
      <div aria-live="polite" class="sr-only" role="status">
        {{ srAnnouncement }}
      </div>

      <!-- 鍵盤操作提示 -->
      <div v-if="discoveryStore.hasCandidates" class="keyboard-hint" aria-hidden="true">
        <span class="hint-key">←</span> 跳過
        <span class="hint-separator">|</span>
        <span class="hint-key">→</span> 喜歡
        <span class="hint-separator">|</span>
        <span class="hint-key">Enter</span> 查看詳情
      </div>

      <!-- 操作按鈕 -->
      <div
        v-if="discoveryStore.hasCandidates"
        class="action-buttons"
        role="group"
        aria-label="配對操作"
      >
        <button
          class="action-btn pass-btn"
          :disabled="isAnimating"
          aria-label="跳過此用戶"
          @click="handlePass"
        >
          <Icon name="close-outline" size="lg" decorative class="btn-icon" />
          <span class="btn-text">跳過</span>
          <div class="btn-ripple"></div>
        </button>

        <button
          class="action-btn like-btn"
          :disabled="isAnimating"
          aria-label="喜歡此用戶"
          @click="handleLike"
        >
          <Icon name="heart" size="lg" decorative class="btn-icon" />
          <span class="btn-text">喜歡</span>
          <div class="btn-ripple"></div>
        </button>
      </div>
    </div>

    <!-- 配對成功彈窗 -->
    <MatchModal
      :show="showMatchModal"
      :matched-user="discoveryStore.lastMatchedUser"
      @close="handleCloseMatchModal"
    />

    <!-- 舉報彈窗 -->
    <ReportModal
      :show="showReportModal"
      :reported-user="reportTarget"
      @close="handleCloseReportModal"
      @reported="handleReported"
    />

    <!-- 用戶詳情彈窗 -->
    <UserDetailModal :show="showUserDetail" :user="selectedUser || {}" @close="closeUserDetail" />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useDiscoveryStore } from '@/stores/discovery'
import Icon from '@/components/ui/Icon.vue'
import MatchModal from '@/components/MatchModal.vue'
import ReportModal from '@/components/ReportModal.vue'
import UserDetailModal from '@/components/UserDetailModal.vue'
import HeartLoader from '@/components/ui/HeartLoader.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { logger } from '@/utils/logger'

const message = useMessage()
const discoveryStore = useDiscoveryStore()

// 預設頭像（圖片加載失敗時使用）
const defaultAvatar = '/default-avatar.svg'

// 螢幕閱讀器播報文字
const srAnnouncement = ref('')

// 動畫狀態
const isAnimating = ref(false)
const exitDirection = ref('')

// 配對成功彈窗
const showMatchModal = ref(false)

// 舉報彈窗
const showReportModal = ref(false)
const reportTarget = ref(null)

// 用戶詳情彈窗
const showUserDetail = ref(false)
const selectedUser = ref(null)

// 顯示的候選人（最多顯示 3 張卡片）
const visibleCandidates = computed(() => {
  return discoveryStore.candidates.slice(0, 3)
})

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

// 當前候選人的 aria-label
const currentCandidateAria = computed(() => {
  const c = discoveryStore.currentCandidate
  if (!c) return '沒有候選人'
  const parts = [`候選人：${c.display_name}，${c.age}歲`]
  if (c.distance_km) parts.push(`距離${formatDistance(c.distance_km)}`)
  if (c.match_score) parts.push(`配對分數${c.match_score}%`)
  parts.push('按左方向鍵跳過，右方向鍵喜歡，Enter查看詳情')
  return parts.join('，')
})

/**
 * 播報螢幕閱讀器訊息
 */
const announce = (text) => {
  // 先清空再設值，確保相同文字也能重新播報
  srAnnouncement.value = ''
  nextTick(() => {
    srAnnouncement.value = text
  })
}

/**
 * 鍵盤事件處理
 */
const handleKeydown = (event) => {
  // 在輸入框內不攔截方向鍵
  const tag = event.target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || event.target.isContentEditable) return

  if (isAnimating.value || !discoveryStore.currentCandidate) return

  switch (event.key) {
    case 'ArrowLeft':
      event.preventDefault()
      handlePass()
      if (isAnimating.value) announce('已跳過')
      break
    case 'ArrowRight':
      event.preventDefault()
      handleLike()
      if (isAnimating.value) announce('已喜歡')
      break
    case 'Enter':
      event.preventDefault()
      openUserDetail(discoveryStore.currentCandidate)
      break
  }
}

/**
 * 載入候選人列表
 */
const loadCandidates = async () => {
  try {
    await discoveryStore.browseCandidates(20)
  } catch (error) {
    logger.error('載入候選人失敗:', error)
  }
}

/**
 * 等待退場動畫完成
 */
const waitForExitAnimation = () => {
  return new Promise((resolve) => {
    const card = document.querySelector('.top-card')
    if (!card) return resolve()

    const cleanup = () => {
      card.removeEventListener('animationend', onEnd)
      clearTimeout(timer)
      resolve()
    }
    const onEnd = () => cleanup()
    card.addEventListener('animationend', onEnd, { once: true })
    // 安全逾時：與動畫時長 0.35s 匹配，加上緩衝
    const timer = setTimeout(cleanup, 400)
  })
}

/**
 * 統一處理卡片退場動作（喜歡/跳過）
 */
const handleCardAction = async (direction, apiCall) => {
  if (!discoveryStore.currentCandidate || isAnimating.value) return

  isAnimating.value = true
  const userId = discoveryStore.currentCandidate.user_id

  // 動畫與 API 同時進行
  exitDirection.value = direction
  const [, result] = await Promise.all([
    waitForExitAnimation(),
    apiCall(userId).catch((error) => {
      logger.error('操作失敗:', error)
      message.error(discoveryStore.error || '操作失敗，請稍後再試')
      return null
    })
  ])

  exitDirection.value = ''

  if (result?.matched) {
    showMatchModal.value = true
  }

  if (discoveryStore.candidates.length < 5) {
    loadCandidates()
  }

  isAnimating.value = false
}

// isAnimating 已防止重複執行，不需額外 throttle
const handleLike = () => handleCardAction('right', (uid) => discoveryStore.likeUser(uid))
const handlePass = () => handleCardAction('left', (uid) => discoveryStore.passUser(uid))

/**
 * 關閉配對成功彈窗
 */
const handleCloseMatchModal = () => {
  showMatchModal.value = false
  discoveryStore.clearLastMatch()
}

/**
 * 開啟舉報彈窗
 */
const handleOpenReportModal = (candidate) => {
  reportTarget.value = candidate
  showReportModal.value = true
}

/**
 * 關閉舉報彈窗
 */
const handleCloseReportModal = () => {
  showReportModal.value = false
  reportTarget.value = null
}

/**
 * 舉報成功處理
 */
const handleReported = () => {
  // 舉報成功後，自動跳過該用戶
  if (discoveryStore.currentCandidate) {
    handlePass()
  }
}

/**
 * 開啟用戶詳情彈窗
 */
const openUserDetail = (candidate) => {
  selectedUser.value = candidate
  showUserDetail.value = true
}

/**
 * 關閉用戶詳情彈窗
 */
const closeUserDetail = () => {
  showUserDetail.value = false
  selectedUser.value = null
}

// 綁定全域事件監聽器
onMounted(async () => {
  document.addEventListener('keydown', handleKeydown)
  await loadCandidates()
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.discovery {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--color-primary-50) 0%, var(--color-primary-100) 100%);
  padding: var(--space-5);
}

.container {
  max-width: 600px;
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
  font-size: var(--font-size-base);
}

.page-title {
  text-align: center;
  font-size: var(--font-size-4xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: var(--space-8);
}

/* 載入中 */
.loading {
  text-align: center;
  padding: var(--space-16) var(--space-5);
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 錯誤訊息 */
.error-message {
  text-align: center;
  padding: var(--space-10) var(--space-5);
}

.error-message p {
  color: var(--color-error-500);
  font-size: var(--font-size-base);
  margin-bottom: var(--space-5);
}

.btn-retry {
  padding: var(--space-3) var(--space-8);
  background: var(--color-like);
  color: white;
  border: none;
  border-radius: var(--radius-full);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--duration-slow) var(--easing-default);
}

.btn-retry:hover {
  background: var(--color-like-hover);
  transform: translateY(-2px);
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: var(--space-16) var(--space-5);
}

.empty-icon {
  margin-bottom: var(--space-5);
  color: var(--color-like);
}

/* 放大空狀態搜尋圖標 */
.empty-search-icon {
  transform: scale(1.67); /* 80px / 48px ≈ 1.67 */
}

.empty-state h2 {
  font-size: var(--font-size-2xl);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.empty-state p {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  margin-bottom: var(--space-8);
}

.btn-refresh {
  padding: var(--space-3) var(--space-8);
  background: var(--color-like);
  color: white;
  border: none;
  border-radius: var(--radius-full);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--duration-slow) var(--easing-default);
}

.btn-refresh:hover {
  background: var(--color-like-hover);
  transform: translateY(-2px);
}

/* 鍵盤操作提示 */
.keyboard-hint {
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-2);
}

.hint-key {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.hint-separator {
  margin: 0 var(--space-2);
  color: var(--color-border);
}

/* 卡片容器 */
.cards-container {
  position: relative;
  width: 100%;
  height: min(600px, 70vh);
  margin-bottom: var(--space-8);
}

/* 候選人卡片 */
.candidate-card {
  position: absolute;
  width: 100%;
  height: 100%;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  transition:
    transform 0.3s ease,
    opacity 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.8);
}

.candidate-card:nth-child(2) {
  transform: scale(0.95) translateY(10px);
  opacity: 0.8;
  z-index: 1;
}

.candidate-card:nth-child(3) {
  transform: scale(0.9) translateY(20px);
  opacity: 0.6;
  z-index: 0;
}

.top-card {
  z-index: 10;
  will-change: transform, opacity;
}

.top-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}

/* 卡片退場動畫 — 使用 @keyframes 取代 transition，更流暢 */
.candidate-card.exit-right {
  animation: exit-right 0.35s var(--easing-default) forwards;
}

.candidate-card.exit-left {
  animation: exit-left 0.35s var(--easing-default) forwards;
}

@keyframes exit-right {
  0% {
    transform: translateX(0) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateX(120%) rotate(15deg);
    opacity: 0;
  }
}

@keyframes exit-left {
  0% {
    transform: translateX(0) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateX(-120%) rotate(-15deg);
    opacity: 0;
  }
}

/* 卡片圖片 */
.card-image {
  position: relative;
  width: 100%;
  height: 360px; /* 減少高度以確保 card-info 完全顯示 */
  overflow: hidden;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff6b6b, #ff8e53);
  color: white;
  font-size: 120px;
  font-weight: bold;
}

/* 配對分數標籤 */
.match-score {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 8px 16px;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.score-icon {
  display: inline-flex;
  color: var(--color-like);
}

.score-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  color: var(--color-like-accessible);
}

/* 舉報按鈕 */
.report-btn {
  position: absolute;
  top: 20px;
  left: 20px;
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.95);
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xl);
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  z-index: 10;
}

.report-btn:hover {
  background: var(--color-surface);
  transform: scale(1.1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.report-btn:active {
  transform: scale(0.95);
}

/* 卡片資訊 */
.card-info {
  padding: var(--space-5);
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.top-card .card-info:hover {
  background-color: var(--color-surface-hover);
}

.card-header {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.card-name {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.card-age {
  font-size: var(--font-size-2xl);
  color: var(--color-text-muted);
}

.card-distance {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-4);
}

.distance-icon {
  display: inline-flex;
}

.card-interests {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}

.interest-tag {
  display: inline-block;
  padding: var(--space-2) var(--space-3);
  background: var(--color-primary-alpha-10);
  color: var(--color-primary-600);
  border-radius: var(--radius-lg);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.card-bio {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  line-height: 1.5;
  margin: 0;
}

/* 點擊查看詳情提示 */
.view-detail-hint {
  margin-top: var(--space-3);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-like-accessible);
  font-weight: var(--font-weight-medium);
  transition: all var(--duration-normal) var(--easing-default);
}

.top-card .card-info:hover .view-detail-hint {
  color: var(--color-like-hover);
  transform: scale(1.05);
}

/* 操作按鈕 */
.action-buttons {
  display: flex;
  justify-content: center;
  gap: var(--space-10);
  padding: var(--space-5) 0;
}

.action-btn {
  position: relative;
  width: 90px;
  height: 90px;
  border: none;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.action-btn::before {
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
    width 0.6s,
    height 0.6s;
}

.action-btn:active::before {
  width: 300px;
  height: 300px;
  transition:
    width 0s,
    height 0s;
}

.action-btn:hover:not(:disabled) {
  transform: scale(1.15) translateY(-3px);
}

.action-btn:active:not(:disabled) {
  transform: scale(1.05);
}

.action-btn:focus-visible {
  outline: 3px solid var(--color-primary-600);
  outline-offset: 4px;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pass-btn {
  background: var(--color-background-light);
  color: var(--color-text-muted);
  border: 3px solid var(--color-border);
}

.pass-btn:hover:not(:disabled) {
  background: var(--color-border);
  color: var(--color-text-primary);
  border-color: var(--color-border);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.like-btn {
  background: var(--color-like-gradient);
  color: white;
  border: 3px solid transparent;
}

.like-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-like-hover), var(--color-like));
  box-shadow: var(--shadow-like-hover);
}

.action-btn .btn-icon {
  display: flex;
  position: relative;
  z-index: 1;
  transition: transform var(--duration-slow) var(--easing-default);
}

.action-btn:hover:not(:disabled) .btn-icon {
  transform: scale(1.1);
}

.btn-text {
  font-size: var(--font-size-xs);
  font-weight: 700;
  margin-top: var(--space-1);
  position: relative;
  z-index: 1;
  letter-spacing: 0.5px;
}

.btn-ripple {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .cards-container {
    height: min(500px, 65vh);
  }

  .card-image {
    height: 350px;
  }

  .card-name {
    font-size: 24px;
  }

  .action-btn {
    width: 75px;
    height: 75px;
  }

  .btn-icon {
    font-size: 32px;
  }
}

@media (max-width: 480px) {
  .cards-container {
    height: min(450px, 60vh);
  }

  .card-image {
    height: 280px;
  }

  .action-buttons {
    gap: var(--space-6);
  }

  .action-btn {
    width: 70px;
    height: 70px;
  }
}

/* 功能性動畫：卡片退場與晉升需要視覺回饋，在減少動態偏好下保留但用更柔和的效果 */
@media (prefers-reduced-motion: reduce) {
  .candidate-card.exit-right,
  .candidate-card.exit-left {
    animation-duration: 0.3s !important;
  }

  .candidate-card {
    transition-duration: 0.25s !important;
  }
}
</style>
