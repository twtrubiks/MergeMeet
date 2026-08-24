<!--
  LikesYou.vue
  誰喜歡我頁面 - 列出喜歡我但我尚未回應的用戶

  從這頁按喜歡必定觸發配對（對方已喜歡我），
  跳過則 24 小時內不再出現（與探索列表同一套規則）。
-->
<template>
  <div class="likes-you">
    <div class="container">
      <!-- 返回主選單按鈕 -->
      <router-link to="/" class="back-home-btn" aria-label="返回主選單">
        <Icon name="home" size="sm" decorative class="btn-icon" />
        <span class="btn-text">返回主選單</span>
      </router-link>

      <h1 class="page-title">
        <Icon name="heart-half" size="lg" decorative class="title-heart-icon" />
        誰喜歡我
      </h1>

      <!-- 載入中 - 使用 Skeleton Loader -->
      <div
        v-if="discoveryStore.likesYouLoading && discoveryStore.likesYou.length === 0"
        class="loading-skeleton"
      >
        <div class="likers-grid">
          <SkeletonCard v-for="i in 4" :key="i" />
        </div>
      </div>

      <!-- 錯誤訊息 -->
      <div v-else-if="discoveryStore.error" class="error-message" role="alert">
        <div class="error-icon" aria-hidden="true">
          <Icon name="alert-outline" size="xl" decorative />
        </div>
        <p>{{ discoveryStore.error }}</p>
        <AnimatedButton variant="danger" @click="loadLikesYou">
          <Icon name="refresh" size="sm" decorative />
          重試
        </AnimatedButton>
      </div>

      <!-- 空狀態 -->
      <div v-else-if="!discoveryStore.hasLikesYou" class="empty-state">
        <div class="empty-icon" aria-hidden="true">
          <Icon name="heart-outline" size="xl" decorative class="empty-heart-icon" />
        </div>
        <h2>還沒有人喜歡你</h2>
        <p>多去探索、完善你的個人檔案，讓更多人認識你！</p>
        <AnimatedButton variant="primary" @click="$router.push('/discovery')">
          <Icon name="search" size="sm" decorative />
          開始探索
        </AnimatedButton>
        <p class="empty-matched-hint">
          已配對的對象請到<router-link to="/matches" class="matches-link">配對列表</router-link>查看
        </p>
      </div>

      <!-- 喜歡我的人列表 -->
      <div v-else>
        <div class="likers-stats">
          <Badge variant="success" size="large">
            {{ discoveryStore.likesYou.length }} 人喜歡你
          </Badge>
          <p class="likers-hint">回喜歡就會立即配對成功！</p>
        </div>

        <div class="likers-grid">
          <div
            v-for="(liker, index) in discoveryStore.likesYou"
            :key="liker.user_id"
            class="liker-card"
            :style="{ animationDelay: `${index * 0.1}s` }"
          >
            <!-- 用戶頭像（可點擊查看詳情） -->
            <div class="liker-avatar clickable" @click="openUserDetail(liker)">
              <div class="avatar-ring" :class="{ online: isOnline(liker.last_active) }">
                <img
                  v-if="liker.photos && liker.photos.length > 0"
                  :src="liker.photos[0]"
                  :alt="liker.display_name"
                />
                <div v-else class="avatar-placeholder">
                  {{ (liker.display_name || 'U')[0] }}
                </div>
              </div>
              <div v-if="isOnline(liker.last_active)" class="online-pulse"></div>
            </div>

            <!-- 用戶資訊（可點擊查看詳情） -->
            <div class="liker-info clickable" @click="openUserDetail(liker)">
              <div class="liker-header">
                <h3 class="liker-name">{{ liker.display_name }}</h3>
                <span class="liker-age">{{ liker.age }}</span>
              </div>

              <p v-if="liker.distance_km != null" class="liker-distance">
                <Icon name="location" size="xs" decorative />
                {{ formatDistance(liker.distance_km) }}
              </p>

              <!-- 興趣標籤（共同興趣排前並高亮，作為配對理由） -->
              <div v-if="liker.interests && liker.interests.length > 0" class="liker-interests">
                <span
                  v-for="tag in displayInterests(liker, MAX_LIKER_INTERESTS)"
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
                <span v-if="liker.interests.length > MAX_LIKER_INTERESTS" class="interest-more">
                  +{{ liker.interests.length - MAX_LIKER_INTERESTS }}
                </span>
              </div>
            </div>

            <!-- 操作按鈕 -->
            <div class="liker-actions">
              <button
                class="btn-like-back"
                title="回喜歡（立即配對）"
                :aria-label="`喜歡 ${liker.display_name}，將立即配對成功`"
                :disabled="actingUserId === liker.user_id"
                @click="handleLikeBack(liker)"
              >
                <Icon name="heart" size="md" decorative />
              </button>
              <button
                class="btn-pass"
                title="跳過"
                :aria-label="`跳過 ${liker.display_name}`"
                :disabled="actingUserId === liker.user_id"
                @click="handlePass(liker)"
              >
                <Icon name="close-outline" size="md" decorative />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 配對成功彈窗 -->
    <MatchModal
      :show="showMatchModal"
      :matched-user="discoveryStore.lastMatchedUser"
      @close="handleCloseMatchModal"
    />

    <!-- 用戶詳情彈窗 -->
    <UserDetailModal :show="showUserDetail" :user="selectedUser || {}" @close="closeUserDetail" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useDiscoveryStore } from '@/stores/discovery'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import Badge from '@/components/ui/Badge.vue'
import MatchModal from '@/components/MatchModal.vue'
import UserDetailModal from '@/components/UserDetailModal.vue'
import Icon from '@/components/ui/Icon.vue'
import { displayInterests } from '@/utils/interests'
import { formatDistance } from '@/utils/distance'
import { logger } from '@/utils/logger'

// 卡片最多顯示的興趣數
const MAX_LIKER_INTERESTS = 3

const message = useMessage()
const discoveryStore = useDiscoveryStore()

// 操作中的用戶 ID（防止同一張卡重複點擊）
const actingUserId = ref(null)

// 配對成功彈窗
const showMatchModal = ref(false)

// 用戶詳情 Modal 狀態
const showUserDetail = ref(false)
const selectedUser = ref(null)

/**
 * 載入誰喜歡我列表
 */
const loadLikesYou = async () => {
  try {
    await discoveryStore.fetchLikesYou()
  } catch (error) {
    logger.error('載入誰喜歡我列表失敗:', error)
  }
}

/**
 * 回喜歡（對方已喜歡我，必定觸發配對）
 */
const handleLikeBack = async (liker) => {
  if (actingUserId.value) return
  actingUserId.value = liker.user_id
  try {
    const result = await discoveryStore.likeUser(liker.user_id, liker)
    discoveryStore.removeFromLikesYou(liker.user_id)
    if (result?.is_match) {
      showMatchModal.value = true
    }
  } catch (error) {
    logger.error('回喜歡失敗:', error)
    message.error(discoveryStore.error || '操作失敗，請稍後再試')
  } finally {
    actingUserId.value = null
  }
}

/**
 * 跳過（24 小時內不再出現，與探索列表同一套規則）
 */
const handlePass = async (liker) => {
  if (actingUserId.value) return
  actingUserId.value = liker.user_id
  try {
    await discoveryStore.passUser(liker.user_id)
    discoveryStore.removeFromLikesYou(liker.user_id)
  } catch (error) {
    logger.error('跳過失敗:', error)
    message.error(discoveryStore.error || '操作失敗，請稍後再試')
  } finally {
    actingUserId.value = null
  }
}

/**
 * 關閉配對成功彈窗
 */
const handleCloseMatchModal = () => {
  showMatchModal.value = false
  discoveryStore.clearLastMatch()
}

/**
 * 開啟用戶詳情 Modal
 */
const openUserDetail = (liker) => {
  selectedUser.value = liker
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
 * 判斷是否在線（最近 5 分鐘活躍）
 */
const isOnline = (lastActive) => {
  if (!lastActive) return false
  const lastActiveDate = new Date(lastActive)
  const now = new Date()
  const diffInMinutes = (now - lastActiveDate) / (1000 * 60)
  return diffInMinutes < 5
}

onMounted(() => {
  loadLikesYou()
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

.likes-you {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--color-primary-50) 0%, var(--color-primary-100) 100%);
  padding: var(--space-5);
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

.empty-icon {
  display: inline-flex;
  color: var(--color-like);
  margin-bottom: var(--space-8);
}

/* 放大空狀態愛心圖標 */
.empty-heart-icon {
  transform: scale(2); /* 96px / 48px = 2 */
}

.empty-state h2 {
  font-size: var(--font-size-2xl);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
  font-weight: 700;
}

.empty-state p {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  margin-bottom: var(--space-8);
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

/* 配對後對方會從此頁移到配對列表，提示去向 */
.empty-matched-hint {
  font-size: var(--font-size-sm);
  margin-top: var(--space-6);
  margin-bottom: 0;
}

.matches-link {
  color: var(--color-primary-600);
  font-weight: var(--font-weight-semibold);
  text-decoration: underline;
  text-underline-offset: 3px;
  margin: 0 var(--space-1);
}

.matches-link:hover {
  color: var(--color-primary-700);
}

.matches-link:focus-visible {
  outline: 2px solid var(--color-primary-600);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* 統計與提示 */
.likers-stats {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-8);
}

.likers-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0;
}

/* 網格 */
.likers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 24px;
}

/* 喜歡我的人卡片 */
.liker-card {
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

.liker-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 30px rgba(255, 107, 107, 0.15);
  border-color: rgba(255, 107, 107, 0.3);
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
.liker-avatar {
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
.liker-info {
  flex: 1;
  min-width: 0;
}

.liker-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.liker-name {
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

.liker-age {
  font-size: 1.2rem;
  color: var(--color-text-muted);
  font-weight: 600;
  flex-shrink: 0;
}

.liker-distance {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-2);
  font-weight: var(--font-weight-medium);
}

.liker-interests {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.interest-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  background: var(--color-primary-alpha-10);
  color: var(--color-primary-500);
  border: 1px solid var(--color-primary-alpha-30);
  border-radius: var(--radius-lg);
  font-size: 0.8rem;
  font-weight: 600;
}

/* 共同興趣：實色主色底 + 白字（對比 ≈ 4.9:1，符合 WCAG AA 小字） */
.interest-tag--common {
  gap: var(--space-1);
  background: var(--color-primary-600);
  color: #fff;
  border-color: var(--color-primary-600);
}

.interest-more {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
}

/* 操作按鈕 */
.liker-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex-shrink: 0;
}

.btn-like-back,
.btn-pass {
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.btn-like-back {
  background: var(--color-like-gradient);
  color: white;
}

.btn-like-back:hover:not(:disabled) {
  transform: scale(1.12);
  box-shadow: var(--shadow-like-hover);
}

.btn-pass {
  background: var(--color-background-light);
  color: var(--color-text-muted);
  border: 2px solid var(--color-border);
}

.btn-pass:hover:not(:disabled) {
  background: var(--color-border);
  color: var(--color-text-primary);
  transform: scale(1.12);
}

.btn-like-back:disabled,
.btn-pass:disabled {
  opacity: 0.5;
  cursor: wait;
}

.btn-like-back:focus-visible,
.btn-pass:focus-visible {
  outline: 3px solid var(--color-primary-600);
  outline-offset: 3px;
}

/* 響應式設計 */
@media (max-width: 480px) {
  .likers-grid {
    grid-template-columns: 1fr;
  }

  .liker-card {
    padding: 16px;
    gap: 12px;
  }

  .avatar-ring img,
  .avatar-placeholder {
    width: 70px;
    height: 70px;
  }
}

/* 尊重減少動效偏好 */
@media (prefers-reduced-motion: reduce) {
  .liker-card {
    animation: none;
  }

  .online-pulse {
    animation: none;
  }
}
</style>
