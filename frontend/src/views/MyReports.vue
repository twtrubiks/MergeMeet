<template>
  <div class="my-reports-page">
    <div class="container">
      <!-- 返回按鈕 -->
      <router-link to="/settings" class="back-btn">
        <span class="btn-icon">←</span>
        <span class="btn-text">返回設定</span>
      </router-link>

      <h1 class="page-title">我的舉報記錄</h1>

      <!-- 載入中 -->
      <div v-if="safetyStore.loading" class="loading-state">
        <div class="spinner"></div>
        <p>載入中...</p>
      </div>

      <!-- 空狀態 -->
      <div v-else-if="safetyStore.myReports.length === 0" class="empty-state">
        <div class="empty-icon">📋</div>
        <h2>暫無舉報記錄</h2>
        <p>您尚未提交任何舉報</p>
      </div>

      <!-- 舉報列表 -->
      <div v-else class="reports-list">
        <div
          v-for="report in safetyStore.myReports"
          :key="report.id"
          class="report-item"
        >
          <!-- 舉報頭部 -->
          <div class="report-header">
            <span class="report-type" :class="getTypeClass(report.report_type)">
              {{ getTypeText(report.report_type) }}
            </span>
            <span class="report-status" :class="getStatusClass(report.status)">
              {{ getStatusText(report.status) }}
            </span>
          </div>

          <!-- 舉報內容 -->
          <div class="report-content">
            <p class="report-reason">{{ report.reason }}</p>
          </div>

          <!-- 舉報時間 -->
          <div class="report-footer">
            <span class="report-time">{{ formatTime(report.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useSafetyStore } from '@/stores/safety'
import { logger } from '@/utils/logger'

const safetyStore = useSafetyStore()

/**
 * 舉報類型文字
 */
const getTypeText = (type) => {
  const types = {
    INAPPROPRIATE: '不當內容',
    HARASSMENT: '騷擾行為',
    FAKE: '假帳號',
    SCAM: '詐騙',
    OTHER: '其他'
  }
  return types[type] || type
}

/**
 * 狀態文字
 */
const getStatusText = (status) => {
  const statuses = {
    PENDING: '處理中',
    UNDER_REVIEW: '審核中',
    RESOLVED: '已處理',
    DISMISSED: '已駁回'
  }
  return statuses[status] || status
}

/**
 * 類型樣式
 */
const getTypeClass = (type) => {
  return `type-${(type || 'other').toLowerCase()}`
}

/**
 * 狀態樣式
 */
const getStatusClass = (status) => {
  return `status-${(status || 'pending').toLowerCase()}`
}

/**
 * 格式化時間
 */
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Lifecycle
onMounted(async () => {
  try {
    await safetyStore.fetchMyReports()
  } catch (error) {
    logger.error('[MyReports] Failed to fetch reports:', error)
  }
})
</script>

<style scoped>
.my-reports-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #FFF5F5 0%, #FFE5E5 100%);
  padding: 20px;
}

.container {
  max-width: 600px;
  margin: 0 auto;
}

/* 返回按鈕 */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.95);
  color: #FF6B6B;
  text-decoration: none;
  border-radius: 25px;
  font-weight: 600;
  font-size: 0.95rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  margin-bottom: 15px;
}

.back-btn:hover {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.3);
}

.back-btn .btn-icon {
  font-size: 1.2rem;
}

.page-title {
  text-align: center;
  font-size: 32px;
  font-weight: 700;
  color: #333;
  margin-bottom: 20px;
}

/* 載入狀態 */
.loading-state {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #FF6B6B;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h2 {
  font-size: 20px;
  color: #333;
  margin: 0 0 8px;
}

.empty-state p {
  font-size: 14px;
  color: #999;
  margin: 0;
}

/* 舉報列表 */
.reports-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.report-item {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

/* 舉報頭部 */
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.report-type {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.type-inappropriate {
  background: #ffe0e0;
  color: #c33;
}

.type-harassment {
  background: #fff3e0;
  color: #e65100;
}

.type-fake {
  background: #e0e7ff;
  color: #3949ab;
}

.type-scam {
  background: #fce4ec;
  color: #c2185b;
}

.type-other {
  background: #f5f5f5;
  color: #666;
}

.report-status {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.status-pending,
.status-under_review {
  background: #fff8e1;
  color: #f9a825;
}

.status-resolved {
  background: #e8f5e9;
  color: #4caf50;
}

.status-dismissed {
  background: #f5f5f5;
  color: #999;
}

/* 舉報內容 */
.report-content {
  margin-bottom: 12px;
}

.report-reason {
  margin: 0;
  font-size: 15px;
  color: #333;
  line-height: 1.5;
}

/* 舉報時間 */
.report-footer {
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}

.report-time {
  font-size: 13px;
  color: #999;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .report-item {
    padding: 16px;
  }

  .report-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
