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
      <div v-if="discoveryStore.loading && !discoveryStore.currentCandidate" class="loading">
        <HeartLoader text="尋找你的真命天子..." />
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
      <div v-else class="cards-container">
        <!-- 候選人卡片 -->
        <div
          v-for="(candidate, index) in visibleCandidates"
          :key="candidate.user_id"
          class="candidate-card"
          :class="{ 'top-card': index === 0 }"
          :style="index === 0 ? cardStyle : {}"
        >
          <!-- 照片 -->
          <div class="card-image">
            <img
              v-if="candidate.photos?.length"
              :src="candidate.photos[0]"
              :alt="candidate.display_name"
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
          <div class="card-info" @click.stop="index === 0 ? openUserDetail(candidate) : null">
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

          <!-- 滑動提示覆蓋層 -->
          <div v-if="index === 0" class="swipe-overlay" aria-hidden="true">
            <div class="swipe-indicator like" :style="{ opacity: likeOpacity }">
              <Icon name="heart" size="lg" decorative class="indicator-icon" />
              <span class="indicator-text">喜歡</span>
            </div>
            <div class="swipe-indicator pass" :style="{ opacity: passOpacity }">
              <Icon name="close-outline" size="lg" decorative class="indicator-icon" />
              <span class="indicator-text">跳過</span>
            </div>
          </div>
        </div>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useDiscoveryStore } from '@/stores/discovery'
import Icon from '@/components/ui/Icon.vue'
import MatchModal from '@/components/MatchModal.vue'
import ReportModal from '@/components/ReportModal.vue'
import UserDetailModal from '@/components/UserDetailModal.vue'
import HeartLoader from '@/components/ui/HeartLoader.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { throttle } from '@/utils/helpers'
import { logger } from '@/utils/logger'

const message = useMessage()
const discoveryStore = useDiscoveryStore()

// 預設頭像（圖片加載失敗時使用）
const defaultAvatar = '/default-avatar.svg'

// 卡片拖拽狀態
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragCurrentX = ref(0)
const dragCurrentY = ref(0)
const isDragging = ref(false)
const isAnimating = ref(false)

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

// 卡片樣式（根據拖拽位置計算）
const cardStyle = computed(() => {
  if (!isDragging.value) return {}

  const deltaX = dragCurrentX.value - dragStartX.value
  const deltaY = dragCurrentY.value - dragStartY.value
  const rotation = deltaX * 0.1

  return {
    transform: `translate(${deltaX}px, ${deltaY}px) rotate(${rotation}deg)`,
    transition: 'none'
  }
})

// 喜歡指示器透明度
const likeOpacity = computed(() => {
  if (!isDragging.value) return 0
  const deltaX = dragCurrentX.value - dragStartX.value
  return Math.max(0, Math.min(1, deltaX / 100))
})

// 跳過指示器透明度
const passOpacity = computed(() => {
  if (!isDragging.value) return 0
  const deltaX = dragCurrentX.value - dragStartX.value
  return Math.max(0, Math.min(1, -deltaX / 100))
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
 * 處理喜歡（內部實現）
 */
const _handleLike = async () => {
  if (!discoveryStore.currentCandidate || isAnimating.value) return

  isAnimating.value = true
  const userId = discoveryStore.currentCandidate.user_id

  // 動畫：向右滑出
  animateCardExit('right')

  setTimeout(async () => {
    try {
      const result = await discoveryStore.likeUser(userId)

      // 如果配對成功，顯示彈窗
      if (result.matched) {
        showMatchModal.value = true
      }

      // 如果候選人不足，重新載入
      if (discoveryStore.candidates.length < 5) {
        await loadCandidates()
      }
    } catch (error) {
      logger.error('喜歡操作失敗:', error)
      // 使用 store 已解析的錯誤訊息（避免重複解析）
      message.error(discoveryStore.error || '操作失敗，請稍後再試')
    } finally {
      isAnimating.value = false
    }
  }, 300)
}

/**
 * 處理跳過（內部實現）
 */
const _handlePass = async () => {
  if (!discoveryStore.currentCandidate || isAnimating.value) return

  isAnimating.value = true
  const userId = discoveryStore.currentCandidate.user_id

  // 動畫：向左滑出
  animateCardExit('left')

  setTimeout(async () => {
    try {
      await discoveryStore.passUser(userId)

      // 如果候選人不足，重新載入
      if (discoveryStore.candidates.length < 5) {
        await loadCandidates()
      }
    } catch (error) {
      logger.error('跳過操作失敗:', error)
      // 使用 store 已解析的錯誤訊息（避免重複解析）
      message.error(discoveryStore.error || '操作失敗，請稍後再試')
    } finally {
      isAnimating.value = false
    }
  }, 300)
}

// 節流處理：防止快速重複點擊（500ms 間隔）
const handleLike = throttle(_handleLike, 500)
const handlePass = throttle(_handlePass, 500)

/**
 * 卡片退出動畫
 */
const animateCardExit = (direction) => {
  const card = document.querySelector('.top-card')
  if (!card) return

  const distance = direction === 'right' ? 1000 : -1000
  card.style.transition = 'transform 0.3s ease-out'
  card.style.transform = `translateX(${distance}px) rotate(${direction === 'right' ? 20 : -20}deg)`
}

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
  // 只有在非拖拽狀態下才開啟
  if (isDragging.value) return
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

/**
 * 鼠標/觸控事件處理
 */
const handlePointerDown = (event) => {
  if (isAnimating.value) return

  isDragging.value = true
  dragStartX.value = event.clientX || event.touches[0].clientX
  dragStartY.value = event.clientY || event.touches[0].clientY
  dragCurrentX.value = dragStartX.value
  dragCurrentY.value = dragStartY.value
}

const handlePointerMove = (event) => {
  if (!isDragging.value) return

  dragCurrentX.value = event.clientX || event.touches[0].clientX
  dragCurrentY.value = event.clientY || event.touches[0].clientY
}

const handlePointerUp = () => {
  if (!isDragging.value) return

  const deltaX = dragCurrentX.value - dragStartX.value

  // 如果滑動距離超過閾值，執行操作
  if (Math.abs(deltaX) > 100) {
    if (deltaX > 0) {
      handleLike()
    } else {
      handlePass()
    }
  }

  isDragging.value = false
  dragStartX.value = 0
  dragStartY.value = 0
  dragCurrentX.value = 0
  dragCurrentY.value = 0
}

// 綁定全域事件監聽器
onMounted(() => {
  loadCandidates()

  document.addEventListener('mousemove', handlePointerMove)
  document.addEventListener('mouseup', handlePointerUp)
  document.addEventListener('touchmove', handlePointerMove)
  document.addEventListener('touchend', handlePointerUp)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', handlePointerMove)
  document.removeEventListener('mouseup', handlePointerUp)
  document.removeEventListener('touchmove', handlePointerMove)
  document.removeEventListener('touchend', handlePointerUp)
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
  font-size: 0.95rem;
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
  display: flex;
  justify-content: center;
  align-items: center;
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
  padding: 60px 20px;
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
  font-size: 24px;
  color: #333;
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 16px;
  color: #666;
  margin-bottom: 30px;
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

/* 卡片容器 */
.cards-container {
  position: relative;
  width: 100%;
  height: 600px;
  margin-bottom: 30px;
}

/* 候選人卡片 */
.candidate-card {
  position: absolute;
  width: 100%;
  height: 100%;
  background: white;
  border-radius: 20px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  transition:
    transform 0.3s ease,
    opacity 0.3s ease,
    box-shadow 0.3s ease;
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
  cursor: grab;
}

.top-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}

.top-card:active {
  cursor: grabbing;
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
  border-radius: 20px;
  display: flex;
  align-items: center;
  gap: 6px;
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
  font-size: 20px;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  z-index: 10;
}

.report-btn:hover {
  background: #fff;
  transform: scale(1.1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.report-btn:active {
  transform: scale(0.95);
}

/* 卡片資訊 */
.card-info {
  padding: 20px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.top-card .card-info:hover {
  background-color: #fffaf0;
}

.card-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 10px;
}

.card-name {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  margin: 0;
}

.card-age {
  font-size: 24px;
  color: #666;
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
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 15px;
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
  font-size: 14px;
  color: #666;
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

/* 滑動提示覆蓋層 */
.swipe-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 360px; /* 只覆蓋圖片區域，不覆蓋 card-info */
  pointer-events: none;
}

.swipe-indicator {
  position: absolute;
  top: 50px;
  padding: 15px 25px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  font-weight: 700;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.swipe-indicator.like {
  right: 50px;
  background: rgba(56, 142, 60, 0.95);
  color: white;
  border: 3px solid white;
}

.swipe-indicator.pass {
  left: 50px;
  background: rgba(244, 67, 54, 0.9);
  color: white;
  border: 3px solid white;
}

.indicator-icon {
  display: flex;
}

.indicator-text {
  font-size: 20px;
}

/* 操作按鈕 */
.action-buttons {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 20px 0;
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

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pass-btn {
  background: #f5f5f5;
  color: #666;
  border: 3px solid #ddd;
}

.pass-btn:hover:not(:disabled) {
  background: #e0e0e0;
  color: #333;
  border-color: #bbb;
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
  font-size: 12px;
  font-weight: 700;
  margin-top: 5px;
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
    height: 500px;
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
</style>
