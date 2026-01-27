<template>
  <div class="home">
    <div class="container">
      <!-- 頂部標題 -->
      <div class="hero-section">
        <div class="logo-animation">
          <div class="logo-hearts">
            <Icon name="heart" size="xl" decorative class="heart-icon heart-left" />
            <Icon name="heart" size="xl" decorative class="heart-icon heart-right" />
          </div>
        </div>
        <h1>歡迎使用 MergeMeet</h1>
        <p class="subtitle">現代化交友平台 - 完整功能版本</p>
      </div>

      <!-- 認證狀態卡片 -->
      <GlassCard :hoverable="true" variant="primary">
        <template #icon>
          <Icon v-if="userStore.isAuthenticated" name="check-circle" size="lg" decorative />
          <Icon v-else name="lock" size="lg" decorative />
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
                <Icon name="search" size="sm" decorative /> 開始探索
              </AnimatedButton>
              <AnimatedButton
                variant="secondary"
                @click="$router.push('/matches')"
              >
                <Icon name="heart" size="sm" decorative /> 我的配對
              </AnimatedButton>
              <AnimatedButton
                variant="secondary"
                @click="$router.push('/profile')"
              >
                <Icon name="person" size="sm" decorative /> 個人檔案
              </AnimatedButton>
              <AnimatedButton
                variant="danger"
                @click="handleLogout"
              >
                <Icon name="logout" size="sm" decorative /> 登出
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
                <Icon name="flash" size="sm" decorative /> 登入
              </AnimatedButton>
              <AnimatedButton
                variant="secondary"
                @click="$router.push('/register')"
              >
                <Icon name="rocket" size="sm" decorative /> 註冊
              </AnimatedButton>
            </div>
          </div>
        </div>
      </GlassCard>
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
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import GlassCard from '@/components/ui/GlassCard.vue'
import Icon from '@/components/ui/Icon.vue'

const router = useRouter()
const userStore = useUserStore()

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
  background: var(--color-primary-gradient);
  padding: var(--space-10) var(--space-5);
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

.logo-hearts {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.heart-icon {
  color: white;
  filter: drop-shadow(0 8px 16px var(--color-like-alpha-40));
  animation: heartBeat 1.5s infinite, pulse 2s infinite;
}

.heart-left {
  transform: rotate(-15deg);
}

.heart-right {
  transform: rotate(15deg);
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
  color: var(--color-text-primary);
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
  color: var(--color-text-primary);
  font-weight: 600;
  font-size: 1.1rem;
  padding: 12px 24px;
  background: rgba(0, 0, 0, 0.06);
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
  color: var(--color-text-secondary);
  font-size: 1.1rem;
  font-weight: 500;
  text-align: center;
}

.button-group {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

/* 響應式設計 */
@media (max-width: 768px) {
  h1 {
    font-size: 2.5rem;
  }

  .subtitle {
    font-size: 1.1rem;
  }

  .button-grid {
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

  .auth-section h2 {
    font-size: 1.5rem;
  }
}

/* 無障礙：減少動態效果 */
@media (prefers-reduced-motion: reduce) {
  .circle {
    animation: none;
  }

  .heart-icon {
    animation: none;
  }

  .hero-section {
    animation: none;
  }
}
</style>
