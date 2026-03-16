<template>
  <div class="blocked">
    <div class="container">
      <h1 class="page-title">封鎖名單</h1>

      <!-- 載入中 -->
      <div v-if="safetyStore.loading && !safetyStore.hasBlockedUsers" class="loading">
        <div class="spinner"></div>
        <p>載入中...</p>
      </div>

      <!-- 錯誤訊息 -->
      <div v-else-if="safetyStore.error" class="error-message">
        <p><Icon name="close" size="sm" decorative /> {{ safetyStore.error }}</p>
        <button class="btn-retry" @click="loadBlockedUsers">重試</button>
      </div>

      <!-- 空狀態 -->
      <div v-else-if="!safetyStore.hasBlockedUsers" class="empty-state">
        <div class="empty-icon"><Icon name="shield" size="xl" decorative /></div>
        <h2>沒有封鎖任何用戶</h2>
        <p>封鎖的用戶會出現在這裡</p>
        <router-link to="/discovery" class="btn-discover">
          <span>返回探索</span>
        </router-link>
      </div>

      <!-- 封鎖列表 -->
      <div v-else class="blocked-list">
        <div
          v-for="blockedUser in safetyStore.blockedUsers"
          :key="blockedUser.id"
          class="blocked-card"
        >
          <div class="blocked-info">
            <div class="blocked-header">
              <div class="blocked-icon"><Icon name="shield" size="md" decorative /></div>
              <div class="blocked-details">
                <h3 class="blocked-email">{{ blockedUser.blocked_user_display_name }}</h3>
                <p class="blocked-date">封鎖於 {{ formatDate(blockedUser.created_at) }}</p>
              </div>
            </div>

            <div v-if="blockedUser.reason" class="blocked-reason">
              <p class="reason-label">封鎖原因：</p>
              <p class="reason-text">{{ blockedUser.reason }}</p>
            </div>
          </div>

          <div class="blocked-actions">
            <button
              class="btn-unblock"
              :disabled="isUnblocking"
              @click="showUnblockConfirm(blockedUser)"
            >
              {{ isUnblocking === blockedUser.blocked_user_id ? '處理中...' : '解除封鎖' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 解除封鎖確認彈窗 -->
    <Transition name="modal">
      <div
        v-if="unblockTarget"
        class="modal-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="unblock-dialog-title"
        @click="cancelUnblock"
        @keydown.escape="cancelUnblock"
      >
        <div class="modal-container" @click.stop>
          <div class="modal-content">
            <div class="modal-icon">❓</div>
            <h2 id="unblock-dialog-title" class="modal-title">確定要解除封鎖？</h2>
            <p class="modal-subtitle">解除封鎖後，此用戶可能會再次出現在您的探索頁面中。</p>
            <div class="modal-actions">
              <button class="btn-cancel" @click="cancelUnblock">取消</button>
              <button class="btn-confirm" :disabled="!!isUnblocking" @click="confirmUnblock">
                {{ isUnblocking ? '處理中...' : '確定解除' }}
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
import { useSafetyStore } from '@/stores/safety'
import { logger } from '@/utils/logger'
import Icon from '@/components/ui/Icon.vue'

const safetyStore = useSafetyStore()

const unblockTarget = ref(null)
const isUnblocking = ref(null)

/**
 * 格式化日期顯示
 */
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * 載入封鎖列表
 */
const loadBlockedUsers = async () => {
  try {
    await safetyStore.fetchBlockedUsers()
  } catch (error) {
    logger.error('載入封鎖列表失敗:', error)
  }
}

/**
 * 顯示解除封鎖確認彈窗
 */
const showUnblockConfirm = (blockedUser) => {
  unblockTarget.value = blockedUser
}

/**
 * 取消解除封鎖操作
 */
const cancelUnblock = () => {
  unblockTarget.value = null
}

/**
 * 確認解除封鎖
 */
const confirmUnblock = async () => {
  if (!unblockTarget.value || isUnblocking.value) return

  isUnblocking.value = unblockTarget.value.blocked_user_id

  try {
    await safetyStore.unblockUser(unblockTarget.value.blocked_user_id)
    unblockTarget.value = null
  } catch (error) {
    logger.error('解除封鎖失敗:', error)
  } finally {
    isUnblocking.value = null
  }
}

onMounted(() => {
  loadBlockedUsers()
})
</script>

<style scoped>
.blocked {
  min-height: 100vh;
  background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%);
  padding: 20px;
}

.container {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  text-align: center;
  font-size: var(--font-size-4xl);
  font-weight: 700;
  color: var(--color-text-primary);
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
  border: 4px solid var(--color-border-light);
  border-top: 4px solid var(--color-like);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* 錯誤訊息 */
.error-message {
  text-align: center;
  padding: 40px 20px;
}

.error-message p {
  color: var(--color-error-500);
  font-size: var(--font-size-base);
  margin-bottom: 20px;
}

.btn-retry {
  padding: 12px 30px;
  background: var(--color-like);
  color: white;
  border: none;
  border-radius: var(--radius-2xl);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
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
  font-size: 80px;
  margin-bottom: 20px;
}

.empty-state h2 {
  font-size: var(--font-size-2xl);
  color: var(--color-text-primary);
  margin-bottom: 10px;
}

.empty-state p {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  margin-bottom: 30px;
}

.btn-discover {
  display: inline-block;
  padding: 14px 30px;
  background: linear-gradient(135deg, #ff6b6b, #ff8e53);
  color: white;
  text-decoration: none;
  border-radius: var(--radius-2xl);
  font-size: var(--font-size-base);
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.btn-discover:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

/* 封鎖列表 */
.blocked-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 封鎖卡片 */
.blocked-card {
  background: white;
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.blocked-info {
  flex: 1;
}

.blocked-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.blocked-icon {
  font-size: 40px;
  flex-shrink: 0;
}

.blocked-details {
  flex: 1;
}

.blocked-email {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 6px;
}

.blocked-date {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0;
}

.blocked-reason {
  padding: 12px;
  background: var(--color-background-light);
  border-radius: var(--radius-sm);
  border-left: 4px solid var(--color-like);
}

.reason-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 600;
  margin: 0 0 6px;
}

.reason-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.5;
}

.blocked-actions {
  flex-shrink: 0;
}

.btn-unblock {
  padding: 10px 24px;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.btn-unblock:hover:not(:disabled) {
  background: #45a049;
  transform: translateY(-2px);
}

.btn-unblock:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  border-radius: var(--radius-xl);
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
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 12px;
}

.modal-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
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
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-cancel {
  background: var(--color-background-light);
  color: var(--color-text-muted);
}

.btn-cancel:hover {
  background: var(--color-border);
}

.btn-confirm {
  background: #4caf50;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background: #45a049;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  .blocked-card {
    flex-direction: column;
  }

  .blocked-actions {
    width: 100%;
  }

  .btn-unblock {
    width: 100%;
  }
}
</style>
