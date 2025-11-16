<template>
  <div class="home">
    <div class="container">
      <!-- 頂部標題 -->
      <div class="hero-section">
        <div class="logo-animation">
          <span class="logo-heart">💕</span>
        </div>
        <h1>歡迎使用 MergeMeet</h1>
        <p class="subtitle">現代化交友平台 - 完整功能版本</p>
      </div>

      <!-- 認證狀態卡片 -->
      <GlassCard :hoverable="true" variant="primary">
        <template #icon>
          <span v-if="userStore.isAuthenticated">✅</span>
          <span v-else>🔐</span>
        </template>
        <div class="auth-section">
          <h2>{{ userStore.isAuthenticated ? '已登入' : '認證狀態' }}</h2>
          <div v-if="userStore.isAuthenticated" class="auth-info">
            <p class="user-email">{{ userStore.userEmail }}</p>
            <div class="button-grid">
              <AnimatedButton
                variant="primary"
                @click="$router.push('/discovery')"
              >
                🔍 開始探索
              </AnimatedButton>
              <AnimatedButton
                variant="secondary"
                @click="$router.push('/matches')"
              >
                💕 我的配對
              </AnimatedButton>
              <AnimatedButton
                variant="ghost"
                @click="$router.push('/profile')"
              >
                👤 個人檔案
              </AnimatedButton>
              <AnimatedButton
                variant="danger"
                @click="handleLogout"
              >
                🚪 登出
              </AnimatedButton>
            </div>
          </div>
          <div v-else class="auth-actions">
            <p class="info-text">請登入或註冊以使用完整功能</p>
            <div class="button-group">
              <AnimatedButton
                variant="primary"
                @click="$router.push('/login')"
              >
                ✨ 登入
              </AnimatedButton>
              <AnimatedButton
                variant="secondary"
                @click="$router.push('/register')"
              >
                🎉 註冊
              </AnimatedButton>
            </div>
          </div>
        </div>
      </GlassCard>

      <!-- API 狀態卡片 -->
      <GlassCard
        :hoverable="true"
        :variant="apiStatus ? 'success' : loading ? 'default' : 'danger'"
      >
        <template #icon>
          <span v-if="loading">⏳</span>
          <span v-else-if="apiStatus">🚀</span>
          <span v-else>⚠️</span>
        </template>
        <div class="api-section">
          <h2>後端 API 狀態</h2>
          <div v-if="loading" class="status-loading">
            <HeartLoader text="連接中..." />
          </div>
          <div v-else-if="apiStatus" class="status-success">
            <p class="status-message">{{ apiStatus.message }}</p>
            <p class="status-version">版本: <strong>{{ apiStatus.version }}</strong></p>
          </div>
          <div v-else class="status-error">
            <p>無法連接到後端 API</p>
            <small>請確認後端服務已啟動</small>
          </div>
        </div>
      </GlassCard>

      <!-- 功能展示區 -->
      <div class="features-section">
        <h3>已完成功能</h3>
        <div class="features-grid">
          <FeatureCard
            title="Week 1: 認證系統"
            badge="Core"
            :items="[
              '用戶註冊 API',
              '用戶登入 API',
              'JWT 認證機制',
              'Token 刷新功能',
              'Email 驗證',
              '密碼強度驗證',
              '年齡驗證（18+）'
            ]"
          />
          <FeatureCard
            title="Week 2: 個人檔案"
            badge="Profile"
            :items="[
              '個人檔案建立與編輯',
              '照片上傳管理（最多 6 張）',
              '興趣標籤選擇（47 種標籤）',
              '地理位置（PostGIS）',
              '配對偏好設定',
              '檔案完整度檢查'
            ]"
          />
          <FeatureCard
            title="Week 3: 探索與配對"
            badge="Matching"
            :items="[
              '智能配對演算法（多因素評分）',
              '卡片滑動介面',
              '喜歡/跳過操作',
              '互相喜歡自動配對',
              '配對列表管理',
              '配對成功彈窗',
              '取消配對功能'
            ]"
          />
          <FeatureCard
            title="Week 4: 訊息系統"
            badge="Chat"
            :items="[
              '聊天室功能',
              '訊息發送與接收',
              'WebSocket 即時通訊',
              '訊息已讀狀態',
              '對話列表',
              '訊息分頁載入',
              '訊息刪除功能'
            ]"
          />
          <FeatureCard
            title="Week 5: 安全功能"
            badge="Safety"
            :items="[
              '用戶封鎖系統',
              '用戶舉報功能',
              '內容審核（敏感詞過濾）',
              '管理員後台',
              '舉報審核處理',
              '用戶封禁管理',
              '敏感詞管理'
            ]"
          />
        </div>
      </div>
    </div>

    <!-- 裝飾性背景元素 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
      <div class="circle circle-4"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useUserStore } from '@/stores/user'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import GlassCard from '@/components/ui/GlassCard.vue'
import FeatureCard from '@/components/ui/FeatureCard.vue'
import HeartLoader from '@/components/ui/HeartLoader.vue'

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
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40px 20px;
  overflow: hidden;
}

/* 裝飾性背景動畫 */
.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  animation: float 25s infinite ease-in-out;
}

.circle-1 {
  width: 400px;
  height: 400px;
  top: -150px;
  left: -150px;
  animation-delay: 0s;
}

.circle-2 {
  width: 300px;
  height: 300px;
  bottom: -100px;
  right: -100px;
  animation-delay: 5s;
}

.circle-3 {
  width: 200px;
  height: 200px;
  top: 40%;
  right: 5%;
  animation-delay: 10s;
}

.circle-4 {
  width: 250px;
  height: 250px;
  bottom: 30%;
  left: 5%;
  animation-delay: 15s;
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(30px, -30px) scale(1.05);
  }
  50% {
    transform: translate(-20px, 20px) scale(0.95);
  }
  75% {
    transform: translate(25px, 15px) scale(1.02);
  }
}

.container {
  position: relative;
  z-index: 1;
  max-width: 1200px;
  width: 100%;
}

/* Hero Section */
.hero-section {
  text-align: center;
  margin-bottom: 48px;
  animation: fadeIn 0.8s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.logo-animation {
  margin-bottom: 24px;
}

.logo-heart {
  display: inline-block;
  font-size: 5rem;
  animation: heartBeat 1.5s infinite, pulse 2s infinite;
  filter: drop-shadow(0 8px 16px rgba(255, 107, 107, 0.4));
}

@keyframes heartBeat {
  0%, 100% {
    transform: scale(1);
  }
  10%, 30% {
    transform: scale(1.15);
  }
  20%, 40% {
    transform: scale(0.95);
  }
}

@keyframes pulse {
  0%, 100% {
    filter: drop-shadow(0 8px 16px rgba(255, 107, 107, 0.4));
  }
  50% {
    filter: drop-shadow(0 12px 24px rgba(255, 107, 107, 0.6));
  }
}

h1 {
  color: white;
  font-size: 3.5rem;
  font-weight: 800;
  margin-bottom: 16px;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  letter-spacing: -1px;
}

.subtitle {
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.3rem;
  font-weight: 300;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Auth Section */
.auth-section h2 {
  color: #333;
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 24px;
  text-align: center;
}

.auth-info {
  display: flex;
  flex-direction: column;
  gap: 24px;
  align-items: center;
}

.user-email {
  color: #667eea;
  font-weight: 600;
  font-size: 1.1rem;
  padding: 12px 24px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 12px;
}

.button-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  width: 100%;
  max-width: 500px;
}

.auth-actions {
  display: flex;
  flex-direction: column;
  gap: 20px;
  align-items: center;
}

.info-text {
  color: #666;
  font-size: 1.05rem;
  text-align: center;
}

.button-group {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

/* API Section */
.api-section h2 {
  color: #333;
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 20px;
  text-align: center;
}

.status-loading {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.status-success {
  text-align: center;
}

.status-message {
  color: #10b981;
  font-weight: 600;
  font-size: 1.2rem;
  margin-bottom: 12px;
}

.status-version {
  color: #666;
  font-size: 1rem;
}

.status-version strong {
  color: #333;
}

.status-error {
  text-align: center;
  color: #ef4444;
}

.status-error p {
  font-weight: 600;
  font-size: 1.1rem;
  margin-bottom: 8px;
}

.status-error small {
  color: #999;
  font-size: 0.9rem;
}

/* Features Section */
.features-section {
  margin-top: 48px;
  animation: slideUp 0.8s ease-out 0.3s both;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.features-section h3 {
  color: white;
  font-size: 2rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 32px;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

/* 響應式設計 */
@media (max-width: 768px) {
  h1 {
    font-size: 2.5rem;
  }

  .subtitle {
    font-size: 1.1rem;
  }

  .logo-heart {
    font-size: 4rem;
  }

  .button-grid {
    grid-template-columns: 1fr;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .home {
    padding: 20px 16px;
  }

  h1 {
    font-size: 2rem;
  }

  .subtitle {
    font-size: 1rem;
  }

  .logo-heart {
    font-size: 3.5rem;
  }

  .auth-section h2,
  .api-section h2 {
    font-size: 1.5rem;
  }
}
</style>
