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

    <!-- Tab 導航 -->
    <div class="admin-tabs">
      <n-tabs v-model:value="activeTab" type="line" animated @update:value="handleTabChange">
        <n-tab-pane name="dashboard" tab="📊 儀表板">
          <div class="tab-content">
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
        </n-tab-pane>

        <n-tab-pane name="moderation" tab="🛡️ 內容審核">
          <div class="tab-content">
            <!-- 審核統計 -->
            <div class="moderation-stats">
              <h2>審核統計</h2>
              <div class="stats-grid">
                <div class="stat-card">
                  <div class="stat-icon">📝</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ moderationStats.total_sensitive_words }}</div>
                    <div class="stat-label">敏感詞總數</div>
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-icon">✅</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ moderationStats.active_sensitive_words }}</div>
                    <div class="stat-label">啟用敏感詞</div>
                  </div>
                </div>
                <div class="stat-card warning">
                  <div class="stat-icon">⏳</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ moderationStats.pending_appeals }}</div>
                    <div class="stat-label">待審核申訴</div>
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ moderationStats.total_violations_today }}</div>
                    <div class="stat-label">今日違規</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 敏感詞管理 -->
            <div class="sensitive-words-section">
              <div class="section-header">
                <h2>敏感詞管理</h2>
                <n-button type="primary" @click="showAddWordModal = true">新增敏感詞</n-button>
              </div>

              <div class="filter-bar">
                <n-select
                  v-model:value="wordFilters.category"
                  placeholder="選擇分類"
                  :options="categoryOptions"
                  style="width: 200px"
                  clearable
                  @update:value="() => loadSensitiveWords(true)"
                />
                <n-select
                  v-model:value="wordFilters.is_active"
                  placeholder="選擇狀態"
                  :options="activeOptions"
                  style="width: 150px"
                  clearable
                  @update:value="() => loadSensitiveWords(true)"
                />
              </div>

              <n-spin :show="loadingWords">
                <n-data-table
                  :columns="wordColumns"
                  :data="sensitiveWords"
                  :pagination="wordPagination"
                  :bordered="false"
                  @update:page="handleWordPageChange"
                />
              </n-spin>
            </div>

            <!-- 內容申訴管理 -->
            <div class="appeals-section">
              <div class="section-header">
                <h2>內容申訴管理</h2>
                <n-button @click="loadAppeals">刷新</n-button>
              </div>

              <n-spin :show="loadingAppeals">
                <div v-if="appeals.length === 0" class="empty-state">
                  <p>暫無待處理申訴</p>
                </div>

                <div v-else class="appeals-list">
                  <div v-for="appeal in appeals" :key="appeal.id" class="appeal-item">
                    <div class="appeal-header">
                      <n-tag :type="getAppealTypeColor(appeal.appeal_type)">
                        {{ formatAppealType(appeal.appeal_type) }}
                      </n-tag>
                      <n-tag :type="getAppealStatusColor(appeal.status)">
                        {{ formatAppealStatus(appeal.status) }}
                      </n-tag>
                    </div>

                    <div class="appeal-body">
                      <p><strong>用戶 ID:</strong> {{ appeal.user_id }}</p>
                      <p><strong>被拒絕的內容:</strong> {{ appeal.rejected_content }}</p>
                      <p><strong>觸發的違規:</strong> {{ appeal.violations }}</p>
                      <p><strong>申訴理由:</strong> {{ appeal.reason }}</p>
                      <p class="appeal-time">{{ formatDate(appeal.created_at) }}</p>
                    </div>

                    <div class="appeal-actions" v-if="appeal.status === 'PENDING'">
                      <n-input
                        v-model:value="appealResponses[appeal.id]"
                        type="textarea"
                        placeholder="輸入管理員回覆..."
                        :rows="2"
                        style="margin-bottom: 8px"
                      />
                      <div class="action-buttons">
                        <n-button
                          size="small"
                          type="success"
                          @click="() => reviewAppeal(appeal.id, 'APPROVED')"
                        >
                          批准申訴
                        </n-button>
                        <n-button
                          size="small"
                          type="error"
                          @click="() => reviewAppeal(appeal.id, 'REJECTED')"
                        >
                          拒絕申訴
                        </n-button>
                      </div>
                    </div>

                    <div v-if="appeal.status !== 'PENDING' && appeal.admin_response" class="admin-response">
                      <p><strong>管理員回覆:</strong> {{ appeal.admin_response }}</p>
                      <p class="response-time">{{ formatDate(appeal.reviewed_at) }}</p>
                    </div>
                  </div>
                </div>
              </n-spin>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="users" tab="👥 用戶管理">
          <div class="tab-content">
            <!-- 用戶管理統計 -->
            <div class="users-stats-section">
              <h2>用戶統計</h2>
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
                <div class="stat-card danger">
                  <div class="stat-icon">🚫</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ stats.banned_users }}</div>
                    <div class="stat-label">被封禁用戶</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 用戶搜尋和篩選 -->
            <div class="users-management-section">
              <div class="section-header">
                <h2>用戶列表</h2>
                <n-button @click="loadUsers">刷新</n-button>
              </div>

              <div class="filter-bar">
                <n-input
                  v-model:value="userFilters.search"
                  placeholder="搜尋 Email..."
                  style="width: 300px"
                  clearable
                  @keyup.enter="() => loadUsers(true)"
                >
                  <template #prefix>🔍</template>
                </n-input>
                <n-select
                  v-model:value="userFilters.is_active"
                  placeholder="選擇狀態"
                  :options="userStatusOptions"
                  style="width: 150px"
                  clearable
                  @update:value="() => loadUsers(true)"
                />
                <n-button type="primary" @click="() => loadUsers(true)">搜尋</n-button>
              </div>

              <n-spin :show="loadingUsers">
                <n-data-table
                  :columns="userColumns"
                  :data="users"
                  :pagination="userPagination"
                  :bordered="false"
                  @update:page="handleUserPageChange"
                />
              </n-spin>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="photo-moderation" tab="📷 照片審核">
          <div class="tab-content">
            <!-- 照片審核統計 -->
            <div class="photo-stats-section">
              <h2>照片審核統計</h2>
              <div class="stats-grid">
                <div class="stat-card warning">
                  <div class="stat-icon">⏳</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ photoStats.pending_photos }}</div>
                    <div class="stat-label">待審核照片</div>
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-icon">✅</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ photoStats.approved_photos }}</div>
                    <div class="stat-label">已通過</div>
                  </div>
                </div>
                <div class="stat-card danger">
                  <div class="stat-icon">❌</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ photoStats.rejected_photos }}</div>
                    <div class="stat-label">已拒絕</div>
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-value">{{ photoStats.today_reviewed }}</div>
                    <div class="stat-label">今日已審核</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 待審核照片列表 -->
            <div class="pending-photos-section">
              <div class="section-header">
                <h2>待審核照片</h2>
                <n-button @click="loadPendingPhotos">刷新</n-button>
              </div>

              <n-spin :show="loadingPhotos">
                <div v-if="pendingPhotos.length === 0" class="empty-state">
                  <p>暫無待審核照片</p>
                </div>

                <div v-else class="photos-grid">
                  <div
                    v-for="photo in pendingPhotos"
                    :key="photo.id"
                    class="photo-card"
                  >
                    <div class="photo-image" @click="showPhotoDetail(photo)">
                      <img :src="getPhotoUrl(photo.url)" :alt="photo.display_name" />
                    </div>
                    <div class="photo-info">
                      <p class="photo-name"><strong>{{ photo.display_name }}</strong></p>
                      <p class="photo-email">{{ photo.user_email }}</p>
                      <p class="photo-time">{{ formatDate(photo.created_at) }}</p>
                    </div>
                    <div class="photo-actions">
                      <n-button
                        size="small"
                        type="success"
                        @click="reviewPhoto(photo.id, 'APPROVED')"
                      >
                        通過
                      </n-button>
                      <n-button
                        size="small"
                        type="error"
                        @click="showRejectModal(photo)"
                      >
                        拒絕
                      </n-button>
                    </div>
                  </div>
                </div>
              </n-spin>

              <!-- 分頁 -->
              <n-pagination
                v-if="photoTotal > photoPageSize"
                v-model:page="photoPage"
                :page-count="Math.ceil(photoTotal / photoPageSize)"
                @update:page="handlePhotoPageChange"
                style="margin-top: 20px; justify-content: center;"
              />
            </div>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- 封禁用戶 Modal -->
    <n-modal v-model:show="showBanUserModal" preset="dialog" title="封禁用戶">
      <div v-if="banningUser" style="margin-bottom: 16px;">
        <p><strong>用戶:</strong> {{ banningUser.email }}</p>
        <p><strong>信任分數:</strong> {{ banningUser.trust_score }}</p>
      </div>
      <n-form>
        <n-form-item label="封禁原因">
          <n-input
            v-model:value="banReason"
            type="textarea"
            placeholder="請輸入封禁原因"
            :rows="3"
          />
        </n-form-item>
        <n-form-item label="封禁天數">
          <n-input-number
            v-model:value="banDurationDays"
            :min="0"
            placeholder="留空或 0 表示永久封禁"
            style="width: 100%"
          />
          <template #feedback>
            <span style="color: #999; font-size: 12px;">留空或設為 0 表示永久封禁</span>
          </template>
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="showBanUserModal = false">取消</n-button>
        <n-button type="error" @click="confirmBanUser">確認封禁</n-button>
      </template>
    </n-modal>

    <!-- 拒絕照片理由 Modal -->
    <n-modal v-model:show="showRejectReasonModal" preset="dialog" title="拒絕照片">
      <n-form>
        <n-form-item label="拒絕理由">
          <n-select
            v-model:value="rejectReason"
            :options="rejectReasonOptions"
            placeholder="選擇拒絕理由"
          />
        </n-form-item>
        <n-form-item v-if="rejectReason === 'OTHER'" label="其他原因">
          <n-input
            v-model:value="customRejectReason"
            type="textarea"
            placeholder="請說明拒絕原因"
            :rows="3"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="showRejectReasonModal = false">取消</n-button>
        <n-button type="error" @click="confirmRejectPhoto">確認拒絕</n-button>
      </template>
    </n-modal>

    <!-- 照片詳情 Modal -->
    <n-modal v-model:show="showPhotoDetailModal" preset="card" title="照片詳情" style="width: 600px">
      <div v-if="selectedPhoto" class="photo-detail">
        <img :src="getPhotoUrl(selectedPhoto.url)" style="max-width: 100%; border-radius: 8px;" />
        <div class="detail-info">
          <p><strong>用戶:</strong> {{ selectedPhoto.display_name }}</p>
          <p><strong>Email:</strong> {{ selectedPhoto.user_email }}</p>
          <p><strong>尺寸:</strong> {{ selectedPhoto.width }} x {{ selectedPhoto.height }}</p>
          <p><strong>大小:</strong> {{ formatFileSize(selectedPhoto.file_size) }}</p>
          <p><strong>上傳時間:</strong> {{ formatDate(selectedPhoto.created_at) }}</p>
        </div>
        <div class="detail-actions" style="margin-top: 16px; display: flex; gap: 8px;">
          <n-button type="success" @click="reviewPhoto(selectedPhoto.id, 'APPROVED'); showPhotoDetailModal = false">
            通過
          </n-button>
          <n-button type="error" @click="showRejectModal(selectedPhoto); showPhotoDetailModal = false">
            拒絕
          </n-button>
        </div>
      </div>
    </n-modal>

    <!-- 新增敏感詞 Modal -->
    <n-modal v-model:show="showAddWordModal" preset="dialog" title="新增敏感詞">
      <n-form ref="wordFormRef" :model="newWord" :rules="wordFormRules">
        <n-form-item label="敏感詞" path="word">
          <n-input v-model:value="newWord.word" placeholder="輸入敏感詞" />
        </n-form-item>

        <n-form-item label="分類" path="category">
          <n-select v-model:value="newWord.category" :options="categoryOptions" />
        </n-form-item>

        <n-form-item label="嚴重程度" path="severity">
          <n-select v-model:value="newWord.severity" :options="severityOptions" />
        </n-form-item>

        <n-form-item label="處理動作" path="action">
          <n-select v-model:value="newWord.action" :options="actionOptions" />
        </n-form-item>

        <n-form-item label="正則表達式">
          <n-checkbox v-model:checked="newWord.is_regex">使用正則表達式</n-checkbox>
        </n-form-item>

        <n-form-item label="描述">
          <n-input
            v-model:value="newWord.description"
            type="textarea"
            placeholder="選填"
            :rows="3"
          />
        </n-form-item>
      </n-form>

      <template #action>
        <n-button @click="showAddWordModal = false">取消</n-button>
        <n-button type="primary" @click="handleAddWord">新增</n-button>
      </template>
    </n-modal>

    <!-- 編輯敏感詞 Modal -->
    <n-modal v-model:show="showEditWordModal" preset="dialog" title="編輯敏感詞">
      <n-form ref="editFormRef" :model="editingWord" :rules="wordFormRules">
        <n-form-item label="敏感詞">
          <n-input :value="editingWord.word" disabled />
        </n-form-item>

        <n-form-item label="分類" path="category">
          <n-select v-model:value="editingWord.category" :options="categoryOptions" />
        </n-form-item>

        <n-form-item label="嚴重程度" path="severity">
          <n-select v-model:value="editingWord.severity" :options="severityOptions" />
        </n-form-item>

        <n-form-item label="處理動作" path="action">
          <n-select v-model:value="editingWord.action" :options="actionOptions" />
        </n-form-item>

        <n-form-item label="正則表達式">
          <n-checkbox v-model:checked="editingWord.is_regex">使用正則表達式</n-checkbox>
        </n-form-item>

        <n-form-item label="啟用">
          <n-checkbox v-model:checked="editingWord.is_active">啟用此敏感詞</n-checkbox>
        </n-form-item>

        <n-form-item label="描述">
          <n-input
            v-model:value="editingWord.description"
            type="textarea"
            placeholder="選填"
            :rows="3"
          />
        </n-form-item>
      </n-form>

      <template #action>
        <n-button @click="showEditWordModal = false">取消</n-button>
        <n-button type="primary" @click="handleUpdateWord">更新</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NTag, NSpin, NTabs, NTabPane, NDataTable,
  NSelect, NModal, NForm, NFormItem, NInput, NCheckbox,
  NPagination, NInputNumber,
  useMessage, useDialog
} from 'naive-ui'
import apiClient from '@/api/client'
import { useUserStore } from '@/stores/user'
import { logger } from '@/utils/logger'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()

const activeTab = ref('dashboard')
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

// Moderation related states
const moderationStats = ref({
  total_sensitive_words: 0,
  active_sensitive_words: 0,
  total_appeals: 0,
  pending_appeals: 0,
  approved_appeals: 0,
  rejected_appeals: 0,
  total_violations_today: 0,
  total_violations_this_week: 0,
  total_violations_this_month: 0
})
const sensitiveWords = ref([])
const appeals = ref([])
const appealResponses = ref({})
const loadingWords = ref(false)
const loadingAppeals = ref(false)

// Photo moderation related states
const photoStats = ref({
  total_photos: 0,
  pending_photos: 0,
  approved_photos: 0,
  rejected_photos: 0,
  today_pending: 0,
  today_reviewed: 0
})
const pendingPhotos = ref([])
const loadingPhotos = ref(false)
const photoPage = ref(1)
const photoPageSize = ref(20)
const photoTotal = ref(0)
const showRejectReasonModal = ref(false)
const showPhotoDetailModal = ref(false)
const selectedPhoto = ref(null)
const rejectingPhoto = ref(null)
const rejectReason = ref(null)
const customRejectReason = ref('')

// Reject reason options
const rejectReasonOptions = [
  { label: '裸露內容', value: 'NUDITY' },
  { label: '暴力內容', value: 'VIOLENCE' },
  { label: '仇恨言論', value: 'HATE' },
  { label: '假照片/非本人', value: 'FAKE' },
  { label: '垃圾內容', value: 'SPAM' },
  { label: '其他', value: 'OTHER' }
]

// User management related states
const users = ref([])
const loadingUsers = ref(false)
const userFilters = ref({
  search: '',
  is_active: null
})
const userPagination = ref({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  onChange: (page) => {
    userPagination.value.page = page
    loadUsers()
  }
})
const showBanUserModal = ref(false)
const banningUser = ref(null)
const banReason = ref('')
const banDurationDays = ref(null)

const userStatusOptions = [
  { label: '活躍', value: true },
  { label: '已封禁', value: false }
]

const showAddWordModal = ref(false)
const showEditWordModal = ref(false)
const newWord = ref({
  word: '',
  category: 'OTHER',
  severity: 'MEDIUM',
  action: 'WARN',
  is_regex: false,
  description: ''
})
const editingWord = ref({
  id: '',
  word: '',
  category: 'OTHER',
  severity: 'MEDIUM',
  action: 'WARN',
  is_regex: false,
  is_active: true,
  description: ''
})

const wordFilters = ref({
  category: null,
  is_active: null
})

const wordPagination = ref({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  onChange: (page) => {
    wordPagination.value.page = page
    loadSensitiveWords()
  }
})

// Options
const categoryOptions = [
  { label: '色情相關', value: 'SEXUAL' },
  { label: '詐騙相關', value: 'SCAM' },
  { label: '騷擾相關', value: 'HARASSMENT' },
  { label: '暴力相關', value: 'VIOLENCE' },
  { label: '個人資訊', value: 'PERSONAL_INFO' },
  { label: '其他', value: 'OTHER' }
]

const severityOptions = [
  { label: '低', value: 'LOW' },
  { label: '中', value: 'MEDIUM' },
  { label: '高', value: 'HIGH' },
  { label: '嚴重', value: 'CRITICAL' }
]

const actionOptions = [
  { label: '警告', value: 'WARN' },
  { label: '拒絕', value: 'REJECT' },
  { label: '自動封禁', value: 'AUTO_BAN' }
]

const activeOptions = [
  { label: '啟用', value: true },
  { label: '停用', value: false }
]

// User columns for data table
const userColumns = [
  {
    title: 'Email',
    key: 'email',
    width: 250,
    ellipsis: { tooltip: true }
  },
  {
    title: '狀態',
    key: 'is_active',
    width: 100,
    render: (row) => {
      return h(NTag, {
        type: row.is_active ? 'success' : 'error'
      }, { default: () => row.is_active ? '活躍' : '已封禁' })
    }
  },
  {
    title: '信任分數',
    key: 'trust_score',
    width: 100,
    render: (row) => {
      const score = row.trust_score || 0
      let type = 'success'
      if (score < 50) type = 'error'
      else if (score < 80) type = 'warning'
      return h(NTag, { type }, { default: () => score })
    }
  },
  {
    title: '警告次數',
    key: 'warning_count',
    width: 100
  },
  {
    title: 'Email 驗證',
    key: 'email_verified',
    width: 100,
    render: (row) => row.email_verified ? '✅' : '❌'
  },
  {
    title: '管理員',
    key: 'is_admin',
    width: 80,
    render: (row) => row.is_admin ? '👑' : '-'
  },
  {
    title: '封禁原因',
    key: 'ban_reason',
    width: 150,
    ellipsis: { tooltip: true },
    render: (row) => row.ban_reason || '-'
  },
  {
    title: '註冊時間',
    key: 'created_at',
    width: 180,
    render: (row) => formatDate(row.created_at)
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => {
      if (row.is_admin) {
        return h('span', { style: 'color: #999;' }, '管理員')
      }
      if (row.is_active) {
        return h(NButton, {
          size: 'small',
          type: 'error',
          onClick: () => showBanModal(row)
        }, { default: () => '封禁' })
      } else {
        return h(NButton, {
          size: 'small',
          type: 'success',
          onClick: () => handleUnbanUser(row)
        }, { default: () => '解封' })
      }
    }
  }
]

// Word columns for data table
const wordColumns = [
  {
    title: '敏感詞',
    key: 'word',
    width: 150
  },
  {
    title: '分類',
    key: 'category',
    width: 120,
    render: (row) => {
      const cat = categoryOptions.find(o => o.value === row.category)
      return cat ? cat.label : row.category
    }
  },
  {
    title: '嚴重程度',
    key: 'severity',
    width: 100,
    render: (row) => {
      const sev = severityOptions.find(o => o.value === row.severity)
      return h(NTag, {
        type: row.severity === 'CRITICAL' ? 'error' : row.severity === 'HIGH' ? 'warning' : 'default'
      }, { default: () => sev ? sev.label : row.severity })
    }
  },
  {
    title: '處理動作',
    key: 'action',
    width: 100,
    render: (row) => {
      const act = actionOptions.find(o => o.value === row.action)
      return act ? act.label : row.action
    }
  },
  {
    title: '正則',
    key: 'is_regex',
    width: 80,
    render: (row) => row.is_regex ? '是' : '否'
  },
  {
    title: '狀態',
    key: 'is_active',
    width: 80,
    render: (row) => {
      return h(NTag, {
        type: row.is_active ? 'success' : 'default'
      }, { default: () => row.is_active ? '啟用' : '停用' })
    }
  },
  {
    title: '描述',
    key: 'description',
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => {
      return h('div', { style: 'display: flex; gap: 8px;' }, [
        h(NButton, {
          size: 'small',
          onClick: () => handleEditWord(row)
        }, { default: () => '編輯' }),
        h(NButton, {
          size: 'small',
          type: 'error',
          onClick: () => handleDeleteWord(row.id)
        }, { default: () => '刪除' })
      ])
    }
  }
]

const wordFormRules = {
  word: {
    required: true,
    message: '請輸入敏感詞',
    trigger: 'blur'
  },
  category: {
    required: true,
    message: '請選擇分類',
    trigger: 'change'
  },
  severity: {
    required: true,
    message: '請選擇嚴重程度',
    trigger: 'change'
  },
  action: {
    required: true,
    message: '請選擇處理動作',
    trigger: 'change'
  }
}

// ==================== Dashboard Functions ====================

// 載入統計數據
const loadStats = async () => {
  try {
    const response = await apiClient.get('/admin/stats')
    stats.value = response.data
  } catch (error) {
    logger.error('載入統計數據失敗:', error)
    message.error('載入統計數據失敗')
  }
}

// ==================== Moderation Functions ====================

// 載入審核統計
const loadModerationStats = async () => {
  try {
    const response = await apiClient.get('/moderation/stats')
    moderationStats.value = response.data
  } catch (error) {
    logger.error('載入審核統計失敗:', error)
    message.error('載入審核統計失敗')
  }
}

// 載入敏感詞列表
const loadSensitiveWords = async (resetPage = false) => {
  if (resetPage) {
    wordPagination.value.page = 1
  }

  loadingWords.value = true
  try {
    const params = {
      page: wordPagination.value.page,
      page_size: wordPagination.value.pageSize
    }
    if (wordFilters.value.category) {
      params.category = wordFilters.value.category
    }
    if (wordFilters.value.is_active !== null) {
      params.is_active = wordFilters.value.is_active
    }

    const response = await apiClient.get('/moderation/sensitive-words', { params })
    sensitiveWords.value = response.data.words
    wordPagination.value.itemCount = response.data.total
  } catch (error) {
    logger.error('載入敏感詞失敗:', error)
    message.error('載入敏感詞失敗')
  } finally {
    loadingWords.value = false
  }
}

// 新增敏感詞
const handleAddWord = async () => {
  try {
    await apiClient.post('/moderation/sensitive-words', newWord.value)
    message.success('新增成功')
    showAddWordModal.value = false
    // 重置表單
    newWord.value = {
      word: '',
      category: 'OTHER',
      severity: 'MEDIUM',
      action: 'WARN',
      is_regex: false,
      description: ''
    }
    await loadSensitiveWords()
    await loadModerationStats()
  } catch (error) {
    logger.error('新增敏感詞失敗:', error)
    message.error(error.response?.data?.detail || '新增失敗')
  }
}

// 編輯敏感詞
const handleEditWord = (word) => {
  editingWord.value = { ...word }
  showEditWordModal.value = true
}

// 更新敏感詞
const handleUpdateWord = async () => {
  try {
    const { id, ...updateData } = editingWord.value
    await apiClient.patch(`/moderation/sensitive-words/${id}`, updateData)
    message.success('更新成功')
    showEditWordModal.value = false
    await loadSensitiveWords()
    await loadModerationStats()
  } catch (error) {
    logger.error('更新敏感詞失敗:', error)
    message.error(error.response?.data?.detail || '更新失敗')
  }
}

// 刪除敏感詞（軟刪除）
const handleDeleteWord = (wordId) => {
  dialog.warning({
    title: '確認刪除',
    content: '確定要刪除此敏感詞嗎？此操作為軟刪除，可以稍後重新啟用。',
    positiveText: '確認',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await apiClient.delete(`/moderation/sensitive-words/${wordId}`)
        message.success('刪除成功')
        await loadSensitiveWords()
        await loadModerationStats()
      } catch (error) {
        logger.error('刪除敏感詞失敗:', error)
        message.error('刪除失敗')
      }
    }
  })
}

// 分頁改變
const handleWordPageChange = (page) => {
  wordPagination.value.page = page
  loadSensitiveWords()
}

// 載入申訴列表
const loadAppeals = async () => {
  loadingAppeals.value = true
  try {
    const response = await apiClient.get('/moderation/appeals', {
      params: { status_filter: 'PENDING', page_size: 50 }
    })
    appeals.value = response.data.appeals
  } catch (error) {
    logger.error('載入申訴失敗:', error)
    message.error('載入申訴失敗')
  } finally {
    loadingAppeals.value = false
  }
}

// 審核申訴
const reviewAppeal = async (appealId, status) => {
  const adminResponse = appealResponses.value[appealId]
  if (!adminResponse) {
    message.error('請輸入管理員回覆')
    return
  }

  try {
    await apiClient.post(`/moderation/appeals/${appealId}/review`, {
      status,
      admin_response: adminResponse
    })
    message.success('處理成功')
    delete appealResponses.value[appealId]
    await loadAppeals()
    await loadModerationStats()
  } catch (error) {
    logger.error('處理申訴失敗:', error)
    message.error(error.response?.data?.detail || '處理失敗')
  }
}

// ==================== User Management Functions ====================

// 載入用戶列表
const loadUsers = async (resetPage = false) => {
  if (resetPage) {
    userPagination.value.page = 1
  }

  loadingUsers.value = true
  try {
    const params = {
      page: userPagination.value.page,
      page_size: userPagination.value.pageSize
    }
    if (userFilters.value.search) {
      params.search = userFilters.value.search
    }
    if (userFilters.value.is_active !== null) {
      params.is_active = userFilters.value.is_active
    }

    const response = await apiClient.get('/admin/users', { params })
    users.value = response.data
    // 假設後端返回的是完整列表，這裡簡單處理分頁
    userPagination.value.itemCount = response.data.length
  } catch (error) {
    logger.error('載入用戶列表失敗:', error)
    message.error('載入用戶列表失敗')
  } finally {
    loadingUsers.value = false
  }
}

// 顯示封禁 Modal
const showBanModal = (user) => {
  banningUser.value = user
  banReason.value = ''
  banDurationDays.value = null
  showBanUserModal.value = true
}

// 確認封禁用戶
const confirmBanUser = async () => {
  if (!banReason.value.trim()) {
    message.error('請輸入封禁原因')
    return
  }

  try {
    await apiClient.post('/admin/users/ban', {
      user_id: banningUser.value.id,
      reason: banReason.value.trim(),
      duration_days: banDurationDays.value || null
    })
    message.success('用戶已被封禁')
    showBanUserModal.value = false
    banningUser.value = null
    await loadUsers()
    await loadStats()
  } catch (error) {
    logger.error('封禁用戶失敗:', error)
    message.error(error.response?.data?.detail || '封禁失敗')
  }
}

// 解封用戶
const handleUnbanUser = (user) => {
  dialog.warning({
    title: '確認解封',
    content: `確定要解封用戶 ${user.email} 嗎？`,
    positiveText: '確認解封',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await apiClient.post('/admin/users/unban', {
          user_id: user.id
        })
        message.success('用戶已解封')
        await loadUsers()
        await loadStats()
      } catch (error) {
        logger.error('解封用戶失敗:', error)
        message.error(error.response?.data?.detail || '解封失敗')
      }
    }
  })
}

// 用戶分頁改變
const handleUserPageChange = (page) => {
  userPagination.value.page = page
  loadUsers()
}

// ==================== Photo Moderation Functions ====================

// 載入照片審核統計
const loadPhotoStats = async () => {
  try {
    const response = await apiClient.get('/admin/photos/stats')
    photoStats.value = response.data
  } catch (error) {
    logger.error('載入照片統計失敗:', error)
    message.error('載入照片統計失敗')
  }
}

// 載入待審核照片
const loadPendingPhotos = async () => {
  loadingPhotos.value = true
  try {
    const response = await apiClient.get('/admin/photos/pending', {
      params: {
        page: photoPage.value,
        page_size: photoPageSize.value,
        status: 'PENDING'
      }
    })
    pendingPhotos.value = response.data.photos
    photoTotal.value = response.data.total
  } catch (error) {
    logger.error('載入待審核照片失敗:', error)
    message.error('載入待審核照片失敗')
  } finally {
    loadingPhotos.value = false
  }
}

// 審核照片
const reviewPhoto = async (photoId, status, rejectionReason = null) => {
  try {
    await apiClient.post(`/admin/photos/${photoId}/review`, {
      status,
      rejection_reason: rejectionReason
    })
    message.success(status === 'APPROVED' ? '照片已通過' : '照片已拒絕')
    await loadPendingPhotos()
    await loadPhotoStats()
  } catch (error) {
    logger.error('審核照片失敗:', error)
    message.error(error.response?.data?.detail || '審核失敗')
  }
}

// 顯示拒絕 Modal
const showRejectModal = (photo) => {
  rejectingPhoto.value = photo
  rejectReason.value = null
  customRejectReason.value = ''
  showRejectReasonModal.value = true
}

// 確認拒絕照片
const confirmRejectPhoto = async () => {
  if (!rejectReason.value) {
    message.error('請選擇拒絕理由')
    return
  }

  let reason = rejectReasonOptions.find(o => o.value === rejectReason.value)?.label || rejectReason.value
  if (rejectReason.value === 'OTHER') {
    if (!customRejectReason.value.trim()) {
      message.error('請輸入拒絕原因')
      return
    }
    reason = customRejectReason.value.trim()
  }

  await reviewPhoto(rejectingPhoto.value.id, 'REJECTED', reason)
  showRejectReasonModal.value = false
  rejectingPhoto.value = null
}

// 顯示照片詳情
const showPhotoDetail = (photo) => {
  selectedPhoto.value = photo
  showPhotoDetailModal.value = true
}

// 取得照片 URL（處理相對路徑）
const getPhotoUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  // 後端 URL
  return `http://localhost:8000${url}`
}

// 格式化檔案大小
const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

// 照片分頁改變
const handlePhotoPageChange = (page) => {
  photoPage.value = page
  loadPendingPhotos()
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
    logger.error('載入舉報列表失敗:', error)
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
    logger.error('處理舉報失敗:', error)
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

// Appeal formatting functions
const formatAppealType = (type) => {
  const types = {
    MESSAGE: '訊息',
    PROFILE: '個人檔案',
    PHOTO: '照片'
  }
  return types[type] || type
}

const formatAppealStatus = (status) => {
  const statuses = {
    PENDING: '待處理',
    APPROVED: '已批准',
    REJECTED: '已拒絕'
  }
  return statuses[status] || status
}

const getAppealTypeColor = (type) => {
  const colors = {
    MESSAGE: 'info',
    PROFILE: 'warning',
    PHOTO: 'success'
  }
  return colors[type] || 'default'
}

const getAppealStatusColor = (status) => {
  const colors = {
    PENDING: 'warning',
    APPROVED: 'success',
    REJECTED: 'error'
  }
  return colors[status] || 'default'
}

// 登出
const handleLogout = () => {
  userStore.logout()
  router.push('/admin/login')
}

// Watch tab changes to load data
const handleTabChange = (value) => {
  if (value === 'moderation') {
    loadModerationStats()
    loadSensitiveWords()
    loadAppeals()
  } else if (value === 'users') {
    loadUsers()
  } else if (value === 'photo-moderation') {
    loadPhotoStats()
    loadPendingPhotos()
  }
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

/* Tab styles */
.admin-tabs {
  background: white;
}

.tab-content {
  padding: 40px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Moderation section styles */
.moderation-stats {
  margin-bottom: 40px;
}

.moderation-stats h2 {
  margin-bottom: 24px;
  font-size: 20px;
  font-weight: 600;
}

.sensitive-words-section,
.appeals-section {
  margin-top: 40px;
}

.sensitive-words-section h2,
.appeals-section h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.filter-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.appeals-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.appeal-item {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.appeal-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.appeal-body {
  margin-bottom: 16px;
}

.appeal-body p {
  margin: 8px 0;
  color: #333;
}

.appeal-time {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.appeal-actions {
  margin-top: 12px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.admin-response {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 8px;
  margin-top: 12px;
}

.admin-response p {
  margin: 4px 0;
  color: #666;
}

.response-time {
  font-size: 12px;
  color: #999;
}

/* User management styles */
.users-stats-section,
.users-management-section {
  margin-bottom: 40px;
}

.users-stats-section h2,
.users-management-section h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

/* Photo moderation styles */
.photo-stats-section,
.pending-photos-section {
  margin-bottom: 40px;
}

.photo-stats-section h2,
.pending-photos-section h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.photos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
}

.photo-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.photo-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.photo-image {
  width: 100%;
  height: 200px;
  overflow: hidden;
  cursor: pointer;
  background-color: #f5f7fa;
}

.photo-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}

.photo-image:hover img {
  transform: scale(1.05);
}

.photo-info {
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
}

.photo-info p {
  margin: 4px 0;
}

.photo-name {
  font-size: 14px;
  color: #2c3e50;
}

.photo-email {
  font-size: 12px;
  color: #7f8c8d;
}

.photo-time {
  font-size: 11px;
  color: #bdc3c7;
}

.photo-actions {
  padding: 12px 16px;
  display: flex;
  gap: 8px;
  justify-content: center;
}

.photo-detail {
  text-align: center;
}

.detail-info {
  text-align: left;
  margin-top: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.detail-info p {
  margin: 8px 0;
  color: #666;
}
</style>
