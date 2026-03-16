<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <div class="logo-animation">
          <Icon name="lock" size="xl" decorative />
        </div>
        <h1>忘記密碼</h1>
        <p>輸入您的 Email，我們將發送重置連結</p>
      </div>

      <!-- 成功狀態 -->
      <div v-if="emailSent" class="success-message">
        <div class="success-icon"><Icon name="check-circle" size="xl" decorative /></div>
        <h2>郵件已發送！</h2>
        <p class="success-text">我們已發送密碼重置郵件到</p>
        <p class="email-display">{{ formData.email }}</p>
        <p class="hint-text">
          請查看您的收件匣（包括垃圾郵件）。<br />
          重置鏈接將在 <strong>30 分鐘</strong>後失效。
        </p>
        <AnimatedButton variant="primary" class="return-btn" @click="goToLogin">
          返回登入
        </AnimatedButton>
      </div>

      <!-- 表單 -->
      <form v-else class="auth-form" @submit.prevent="handleSubmit">
        <FloatingInput
          id="email"
          v-model="formData.email"
          label="Email"
          type="email"
          autocomplete="email"
          :disabled="isLoading"
          :required="true"
          :error="error"
        />

        <!-- 速率限制提示 -->
        <p v-if="rateLimitMessage" class="rate-limit-message">
          {{ rateLimitMessage }}
        </p>

        <!-- 送出按鈕 -->
        <AnimatedButton
          type="submit"
          variant="primary"
          :disabled="!isFormValid || isLoading"
          :loading="isLoading"
        >
          <span v-if="!isLoading"><Icon name="chat" size="sm" decorative /> 發送重置郵件</span>
        </AnimatedButton>
      </form>

      <!-- 返回登入 -->
      <div class="auth-footer">
        <p>
          記起密碼了？
          <router-link to="/login" class="login-link">返回登入 →</router-link>
        </p>
      </div>
    </div>

    <!-- 裝飾性背景元素 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/client'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import FloatingInput from '@/components/ui/FloatingInput.vue'
import Icon from '@/components/ui/Icon.vue'

const router = useRouter()

// 表單資料
const formData = ref({
  email: ''
})

// 狀態管理
const isLoading = ref(false)
const error = ref('')
const emailSent = ref(false)
const rateLimitMessage = ref('')

// 計算屬性
const isFormValid = computed(() => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return formData.value.email && emailRegex.test(formData.value.email)
})

// 方法
const handleSubmit = async () => {
  error.value = ''
  rateLimitMessage.value = ''
  isLoading.value = true

  try {
    // API 呼叫 - 無尾隨斜線
    await apiClient.post('/auth/forgot-password', {
      email: formData.value.email
    })

    // 顯示成功狀態
    emailSent.value = true
  } catch (err) {
    if (err.response?.status === 429) {
      // 速率限制
      rateLimitMessage.value = err.response.data.detail
    } else {
      error.value = '發送失敗，請稍後再試'
    }
    console.error('忘記密碼錯誤:', err)
  } finally {
    isLoading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.auth-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-gradient);
  padding: 20px;
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
  background: rgba(255, 255, 255, 0.1);
  animation: float 20s infinite ease-in-out;
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -100px;
  left: -100px;
  animation-delay: 0s;
}

.circle-2 {
  width: 200px;
  height: 200px;
  bottom: -50px;
  right: -50px;
  animation-delay: 5s;
}

.circle-3 {
  width: 150px;
  height: 150px;
  top: 50%;
  right: 10%;
  animation-delay: 10s;
}

@keyframes float {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -30px) scale(1.1);
  }
  66% {
    transform: translate(-20px, 20px) scale(0.9);
  }
}

.auth-card {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  padding: 48px;
  max-width: 450px;
  width: 100%;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.2);
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo-animation {
  margin-bottom: 20px;
}

.logo-icon {
  display: inline-block;
  font-size: 4rem;
  animation: pulse 2s infinite;
  filter: drop-shadow(0 4px 8px var(--color-primary-alpha-30));
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.auth-header h1 {
  font-size: 2.2rem;
  font-weight: 700;
  background: var(--color-primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}

.auth-header p {
  color: var(--color-text-secondary);
  font-size: 1rem;
  font-weight: 500;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rate-limit-message {
  color: #ff9800;
  font-size: 0.9rem;
  text-align: center;
  padding: 12px;
  background: #fff3e0;
  border-radius: 8px;
  margin-top: 8px;
}

.success-message {
  text-align: center;
  padding: 20px 0;
}

.success-icon {
  font-size: 4rem;
  margin-bottom: 20px;
  animation: bounce 0.6s ease-out;
}

@keyframes bounce {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.success-message h2 {
  color: var(--color-success-500);
  font-size: 1.8rem;
  margin-bottom: 16px;
  font-weight: 600;
}

.success-text {
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  font-size: 1rem;
}

.email-display {
  color: var(--color-primary-500);
  font-weight: 600;
  font-size: 1.1rem;
  margin-bottom: 16px;
  word-break: break-all;
}

.hint-text {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  font-weight: 500;
  line-height: 1.6;
  margin-bottom: 24px;
}

.return-btn {
  margin-top: 16px;
}

.auth-footer {
  margin-top: 32px;
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid var(--color-border);
}

.auth-footer p {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
}

.login-link {
  color: var(--color-primary-500);
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.login-link:hover {
  color: var(--color-primary-700);
  gap: 8px;
}

/* 響應式設計 */
@media (max-width: 480px) {
  .auth-card {
    padding: 32px 24px;
  }

  .auth-header h1 {
    font-size: 1.8rem;
  }

  .logo-icon {
    font-size: 3rem;
  }
}
</style>
