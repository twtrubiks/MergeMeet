<template>
  <div class="admin-dashboard">
    <!-- 頂部導航 -->
    <div class="admin-header">
      <h1>MergeMeet 管理後台</h1>
      <div class="header-actions">
        <span class="admin-email">{{ userStore.user?.email }}</span>
        <n-button @click="handleLogout">登出</n-button>
      </div>
    </div>

    <!-- 主要內容 -->
    <div class="admin-content">
      <!-- 統計卡片 -->
      <div class="stats-section">
        <h2>系統統計</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">👥</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_users }}</div>
              <div class="stat-label">總用戶數</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon">✅</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.active_users }}</div>
              <div class="stat-label">活躍用戶</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon">💕</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.active_matches }}</div>
              <div class="stat-label">活躍配對</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon">💬</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_messages }}</div>
              <div class="stat-label">訊息總數</div>
            </div>
          </div>

          <div class="stat-card warning">
            <div class="stat-icon">⚠️</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pending_reports }}</div>
              <div class="stat-label">待處理舉報</div>
            </div>
          </div>

          <div class="stat-card danger">
            <div class="stat-icon">🚫</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.banned_users }}</div>
              <div class="stat-label">被封禁用戶</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 舉報管理 -->
      <div class="reports-section">
        <div class="section-header">
          <h2>舉報管理</h2>
          <n-button @click="loadReports">刷新</n-button>
        </div>

        <n-spin :show="loading">
          <div v-if="reports.length === 0" class="empty-state">
            <p>暫無待處理舉報</p>
          </div>

          <div v-else class="reports-list">
            <div v-for="report in reports" :key="report.id" class="report-item">
              <div class="report-header">
                <n-tag :type="getReportTypeColor(report.report_type)">
                  {{ formatReportType(report.report_type) }}
                </n-tag>
                <n-tag :type="getStatusColor(report.status)">
                  {{ formatStatus(report.status) }}
                </n-tag>
              </div>

              <div class="report-body">
                <p><strong>舉報者:</strong> {{ report.reporter_email }}</p>
                <p><strong>被舉報:</strong> {{ report.reported_user_email }}</p>
                <p><strong>原因:</strong> {{ report.reason }}</p>
                <p class="report-time">{{ formatDate(report.created_at) }}</p>
              </div>

              <div class="report-actions" v-if="report.status === 'PENDING'">
                <n-button size="small" type="success" @click="() => reviewReport(report.id, 'APPROVED', 'WARNING')">
                  批准 (警告)
                </n-button>
                <n-button size="small" type="error" @click="() => reviewReport(report.id, 'APPROVED', 'BAN_USER')">
                  批准 (封禁)
                </n-button>
                <n-button size="small" @click="() => reviewReport(report.id, 'REJECTED', 'NO_ACTION')">
                  拒絕
                </n-button>
              </div>
            </div>
          </div>
        </n-spin>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, NSpin, useMessage } from 'naive-ui'
import apiClient from '@/api/client'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const message = useMessage()
const userStore = useUserStore()

const loading = ref(false)
const stats = ref({
  total_users: 0,
  active_users: 0,
  banned_users: 0,
  total_matches: 0,
  active_matches: 0,
  total_messages: 0,
  total_reports: 0,
  pending_reports: 0,
  total_blocked_users: 0
})
const reports = ref([])

// 載入統計數據
const loadStats = async () => {
  try {
    const response = await apiClient.get('/admin/stats')
    stats.value = response.data
  } catch (error) {
    console.error('載入統計數據失敗:', error)
    message.error('載入統計數據失敗')
  }
}

// 載入舉報列表
const loadReports = async () => {
  loading.value = true
  try {
    const response = await apiClient.get('/admin/reports', {
      params: { status_filter: 'PENDING', page_size: 20 }
    })
    reports.value = response.data
  } catch (error) {
    console.error('載入舉報列表失敗:', error)
    message.error('載入舉報列表失敗')
  } finally {
    loading.value = false
  }
}

// 處理舉報
const reviewReport = async (reportId, status, action) => {
  try {
    await apiClient.post(`/admin/reports/${reportId}/review`, {
      status,
      action,
      admin_notes: `系統自動處理: ${action}`
    })

    message.success('處理成功')
    await loadReports()
    await loadStats()
  } catch (error) {
    console.error('處理舉報失敗:', error)
    message.error('處理失敗')
  }
}

// 格式化函數
const formatReportType = (type) => {
  const types = {
    INAPPROPRIATE: '不當內容',
    HARASSMENT: '騷擾',
    FAKE: '假帳號',
    SCAM: '詐騙',
    OTHER: '其他'
  }
  return types[type] || type
}

const formatStatus = (status) => {
  const statuses = {
    PENDING: '待處理',
    APPROVED: '已批准',
    REJECTED: '已拒絕',
    UNDER_REVIEW: '審查中'
  }
  return statuses[status] || status
}

const getReportTypeColor = (type) => {
  const colors = {
    INAPPROPRIATE: 'warning',
    HARASSMENT: 'error',
    FAKE: 'info',
    SCAM: 'error',
    OTHER: 'default'
  }
  return colors[type] || 'default'
}

const getStatusColor = (status) => {
  const colors = {
    PENDING: 'warning',
    APPROVED: 'success',
    REJECTED: 'default',
    UNDER_REVIEW: 'info'
  }
  return colors[status] || 'default'
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-TW')
}

// 登出
const handleLogout = () => {
  userStore.logout()
  router.push('/admin/login')
}

onMounted(() => {
  loadStats()
  loadReports()
})
</script>

<style scoped>
.admin-dashboard {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.admin-header {
  background: white;
  padding: 20px 40px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.admin-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.admin-email {
  color: #666;
  font-size: 14px;
}

.admin-content {
  padding: 40px;
  max-width: 1400px;
  margin: 0 auto;
}

.stats-section {
  margin-bottom: 40px;
}

.stats-section h2 {
  margin-bottom: 24px;
  font-size: 20px;
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-4px);
}

.stat-card.warning {
  background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
}

.stat-card.danger {
  background: linear-gradient(135deg, #fab1a0 0%, #ff7675 100%);
}

.stat-icon {
  font-size: 40px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #2c3e50;
}

.stat-label {
  font-size: 14px;
  color: #7f8c8d;
  margin-top: 4px;
}

.reports-section h2 {
  margin-bottom: 24px;
  font-size: 20px;
  font-weight: 600;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.report-item {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.report-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.report-body {
  margin-bottom: 16px;
}

.report-body p {
  margin: 8px 0;
  color: #333;
}

.report-time {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.report-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
