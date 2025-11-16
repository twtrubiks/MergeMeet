<template>
  <div class="home">
    <div class="container">
      <h1>🎉 歡迎使用 MergeMeet</h1>
      <p class="subtitle">現代化交友平台 - 完整功能版本</p>

      <!-- 認證狀態卡片 -->
      <div class="card auth-card">
        <h2>認證狀態</h2>
        <div v-if="userStore.isAuthenticated" class="auth-info">
          <p class="success">✅ 已登入</p>
          <p class="user-email">{{ userStore.userEmail }}</p>
          <div class="button-group">
            <router-link to="/discovery" class="btn-primary">🔍 開始探索</router-link>
            <router-link to="/matches" class="btn-primary">💕 我的配對</router-link>
          </div>
          <div class="button-group" style="margin-top: 12px;">
            <router-link to="/profile" class="btn-secondary">個人檔案</router-link>
            <button @click="handleLogout" class="btn-outline">登出</button>
          </div>
        </div>
        <div v-else class="auth-actions">
          <p class="info-text">請登入或註冊以使用完整功能</p>
          <div class="button-group">
            <router-link to="/login" class="btn-primary">登入</router-link>
            <router-link to="/register" class="btn-outline">註冊</router-link>
          </div>
        </div>
      </div>

      <!-- API 狀態卡片 -->
      <div class="card">
        <h2>後端 API 狀態</h2>
        <div v-if="loading">載入中...</div>
        <div v-else-if="apiStatus">
          <p class="success">✅ {{ apiStatus.message }}</p>
          <p>版本: {{ apiStatus.version }}</p>
        </div>
        <div v-else class="error">
          ❌ 無法連接到後端 API
        </div>
      </div>

      <!-- 開發資訊 -->
      <div class="info">
        <h3>已完成功能</h3>
        <div class="features-grid">
          <div class="feature-section">
            <h4>Week 1: 認證系統</h4>
            <ul>
              <li>✅ 用戶註冊 API</li>
              <li>✅ 用戶登入 API</li>
              <li>✅ JWT 認證機制</li>
              <li>✅ Token 刷新功能</li>
              <li>✅ Email 驗證</li>
              <li>✅ 密碼強度驗證</li>
              <li>✅ 年齡驗證（18+）</li>
            </ul>
          </div>
          <div class="feature-section">
            <h4>Week 2: 個人檔案</h4>
            <ul>
              <li>✅ 個人檔案建立與編輯</li>
              <li>✅ 照片上傳管理（最多 6 張）</li>
              <li>✅ 興趣標籤選擇（47 種標籤）</li>
              <li>✅ 地理位置（PostGIS）</li>
              <li>✅ 配對偏好設定</li>
              <li>✅ 檔案完整度檢查</li>
            </ul>
          </div>
          <div class="feature-section">
            <h4>Week 3: 探索與配對</h4>
            <ul>
              <li>✅ 智能配對演算法（多因素評分）</li>
              <li>✅ 卡片滑動介面</li>
              <li>✅ 喜歡/跳過操作</li>
              <li>✅ 互相喜歡自動配對</li>
              <li>✅ 配對列表管理</li>
              <li>✅ 配對成功彈窗</li>
              <li>✅ 取消配對功能</li>
            </ul>
          </div>
          <div class="feature-section">
            <h4>Week 4: 訊息系統</h4>
            <ul>
              <li>✅ 聊天室功能</li>
              <li>✅ 訊息發送與接收</li>
              <li>✅ WebSocket 即時通訊</li>
              <li>✅ 訊息已讀狀態</li>
              <li>✅ 對話列表</li>
              <li>✅ 訊息分頁載入</li>
              <li>✅ 訊息刪除功能</li>
            </ul>
          </div>
          <div class="feature-section">
            <h4>Week 5: 安全功能</h4>
            <ul>
              <li>✅ 用戶封鎖系統</li>
              <li>✅ 用戶舉報功能</li>
              <li>✅ 內容審核（敏感詞過濾）</li>
              <li>✅ 管理員後台</li>
              <li>✅ 舉報審核處理</li>
              <li>✅ 用戶封禁管理</li>
              <li>✅ 敏感詞管理</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const apiStatus = ref(null)

onMounted(async () => {
  try {
    const response = await axios.get('/api/hello')
    apiStatus.value = response.data
  } catch (error) {
    console.error('API 連接失敗:', error)
  } finally {
    loading.value = false
  }
})

/**
 * 處理登出
 */
const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.container {
  max-width: 600px;
  width: 100%;
}

h1 {
  color: white;
  font-size: 3rem;
  margin-bottom: 1rem;
  text-align: center;
}

.subtitle {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.2rem;
  text-align: center;
  margin-bottom: 2rem;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.card h2 {
  color: #333;
  margin-bottom: 1rem;
}

.success {
  color: #10b981;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.error {
  color: #ef4444;
  font-weight: 600;
}

.info {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 1.5rem;
  color: white;
}

.info h3 {
  margin-bottom: 1rem;
}

.info ul {
  list-style: none;
}

.info li {
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.info li:last-child {
  border-bottom: none;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.feature-section h4 {
  margin-bottom: 0.75rem;
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.1rem;
}

.auth-card {
  text-align: center;
}

.auth-info {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
}

.user-email {
  color: #667eea;
  font-weight: 600;
}

.info-text {
  color: #666;
  margin-bottom: 1rem;
}

.auth-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.button-group {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.btn-primary,
.btn-outline,
.btn-secondary {
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border: none;
  font-size: 1rem;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
}

.btn-outline {
  background: transparent;
  color: #667eea;
  border: 2px solid #667eea;
}

.btn-outline:hover {
  background: #667eea;
  color: white;
  transform: translateY(-2px);
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
  transform: translateY(-2px);
}
</style>
