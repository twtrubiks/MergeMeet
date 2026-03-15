<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <div class="logo-animation">
          <div class="logo-hearts">
            <Icon name="heart" size="xl" decorative class="heart-icon heart-main" />
            <Icon name="heart" size="lg" decorative class="heart-icon heart-small" />
          </div>
        </div>
        <h1>歡迎回來</h1>
        <p>登入 MergeMeet 開始配對</p>
      </div>

      <!-- 鎖定警告 -->
      <div v-if="isLocked" class="lockout-warning">
        <div class="lockout-icon"><Icon name="lock" size="xl" decorative /></div>
        <div class="lockout-message">帳號已暫時鎖定</div>
        <div class="lockout-countdown">請於 {{ formatCountdown(lockoutCountdown) }} 後再試</div>
      </div>

      <form v-else class="auth-form" @submit.prevent="handleLogin">
        <!-- Email -->
        <FloatingInput
          id="email"
          v-model="formData.email"
          label="Email"
          type="email"
          autocomplete="email"
          :disabled="isLoading"
          :required="true"
        />

        <!-- 密碼 -->
        <FloatingInput
          id="password"
          v-model="formData.password"
          label="密碼"
          type="password"
          autocomplete="current-password"
          :disabled="isLoading"
          :required="true"
          :error="error"
          :show-password-toggle="true"
        />

        <!-- 剩餘嘗試次數警告 -->
        <div v-if="showAttemptsWarning" class="attempts-warning">
          <Icon name="warning" size="sm" decorative /> 剩餘
          {{ loginLimitInfo.remainingAttempts }} 次嘗試機會
        </div>

        <!-- 忘記密碼連結 -->
        <div class="forgot-password-link">
          <router-link to="/forgot-password">忘記密碼？</router-link>
        </div>

        <!-- 送出按鈕 -->
        <AnimatedButton
          type="submit"
          variant="primary"
          :disabled="!isFormValid"
          :loading="isLoading"
        >
          <span v-if="!isLoading"><Icon name="flash" size="sm" decorative /> 登入</span>
        </AnimatedButton>
      </form>

      <!-- 前往註冊 -->
      <div class="auth-footer">
        <p>
          還沒有帳號？
          <router-link to="/register" class="register-link">立即註冊 →</router-link>
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
import { ref, computed, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import FloatingInput from '@/components/ui/FloatingInput.vue'
import Icon from '@/components/ui/Icon.vue'

const router = useRouter()
const userStore = useUserStore()

// 表單資料
const formData = ref({
  email: '',
  password: ''
})

// 錯誤訊息
const error = ref('')

// 載入狀態
const isLoading = computed(() => userStore.isLoading)

// 登入限制狀態
const loginLimitInfo = computed(() => userStore.loginLimitInfo)
const isLocked = computed(() => loginLimitInfo.value.isLocked)

// 倒計時相關
const lockoutCountdown = ref(0)
let countdownTimer = null

// 是否顯示剩餘次數警告（少於等於 3 次時顯示）
const showAttemptsWarning = computed(() => {
  const remaining = loginLimitInfo.value.remainingAttempts
  return remaining !== null && remaining <= 3 && remaining > 0
})

// 格式化倒計時（分:秒）
const formatCountdown = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 開始倒計時
const startCountdown = (seconds) => {
  lockoutCountdown.value = seconds
  clearInterval(countdownTimer)

  countdownTimer = setInterval(() => {
    lockoutCountdown.value--
    if (lockoutCountdown.value <= 0) {
      clearInterval(countdownTimer)
      // 重置鎖定狀態
      userStore.resetLoginLimitInfo()
    }
  }, 1000)
}

// 監聽鎖定狀態變化
watch(
  () => loginLimitInfo.value.lockoutSeconds,
  (newVal) => {
    if (newVal > 0) {
      startCountdown(newVal)
    }
  }
)

// 清理定時器
onUnmounted(() => {
  clearInterval(countdownTimer)
})

// 表單驗證
const isFormValid = computed(() => {
  return formData.value.email && formData.value.password
})

/**
 * 處理登入
 */
const handleLogin = async () => {
  error.value = ''

  // 呼叫 API
  const success = await userStore.login({
    email: formData.value.email,
    password: formData.value.password
  })

  if (success) {
    // 登入成功，導向首頁
    router.push('/')
  } else {
    // 顯示錯誤訊息
    error.value = userStore.error
  }
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
  padding: var(--space-5);
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
  border-radius: var(--radius-2xl);
  padding: var(--space-12);
  max-width: 450px;
  width: 100%;
  box-shadow:
    var(--shadow-2xl),
    0 0 0 1px rgba(255, 255, 255, 0.2);
  animation: slideUp var(--duration-slower) var(--easing-out);
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

.logo-hearts {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 64px;
}

.heart-icon {
  color: #ff6b6b;
  filter: drop-shadow(0 4px 8px rgba(255, 107, 107, 0.3));
}

.heart-main {
  animation: heartBeat 1.5s infinite;
}

.heart-small {
  position: absolute;
  right: 0;
  bottom: 0;
  color: #f093fb;
  animation: heartBeat 1.5s infinite;
  animation-delay: 0.2s;
}

@keyframes heartBeat {
  0%,
  100% {
    transform: scale(1);
  }
  10%,
  30% {
    transform: scale(1.1);
  }
  20%,
  40% {
    transform: scale(0.9);
  }
}

.auth-header h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  background: var(--color-primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: var(--space-2);
}

.auth-header p {
  color: #555;
  font-size: 1rem;
  font-weight: 500;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 鎖定警告樣式 */
.lockout-warning {
  text-align: center;
  padding: var(--space-8);
  background: var(--color-like-gradient);
  border-radius: var(--radius-md);
  color: white;
  margin-bottom: var(--space-6);
}

.lockout-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.lockout-message {
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.lockout-countdown {
  font-size: 1.5rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

/* 剩餘嘗試次數警告 */
.attempts-warning {
  background: #fff3cd;
  border: 1px solid #ffc107;
  color: #856404;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 0.5rem;
  text-align: center;
  font-weight: 500;
}

.forgot-password-link {
  text-align: right;
  margin-top: 4px;
  margin-bottom: 8px;
}

.forgot-password-link a {
  color: var(--color-primary-600);
  text-decoration: none;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: color var(--duration-slow) var(--easing-default);
}

.forgot-password-link a:hover {
  color: var(--color-primary-700);
  text-decoration: underline;
}

.auth-footer {
  margin-top: 32px;
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid #e0e0e0;
}

.auth-footer p {
  color: #555;
  font-size: 0.95rem;
}

.register-link {
  color: var(--color-primary-600);
  text-decoration: none;
  font-weight: var(--font-weight-semibold);
  transition: all var(--duration-slow) var(--easing-default);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.register-link:hover {
  color: var(--color-primary-700);
  gap: var(--space-2);
}

/* 響應式設計 */
@media (max-width: 480px) {
  .auth-card {
    padding: 32px 24px;
  }

  .auth-header h1 {
    font-size: 1.8rem;
  }

  .logo-hearts {
    width: 64px;
    height: 52px;
  }
}

/* 無障礙：減少動畫 */
@media (prefers-reduced-motion: reduce) {
  .logo-hearts .heart-icon,
  .circle {
    animation: none;
  }

  .auth-card {
    animation: none;
  }
}
</style>
