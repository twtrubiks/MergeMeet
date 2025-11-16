<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <div class="logo-animation">
          <span class="logo-heart">💕</span>
        </div>
        <h1>加入 MergeMeet</h1>
        <p>開始你的交友之旅</p>
      </div>

      <form @submit.prevent="handleRegister" class="auth-form">
        <!-- Email -->
        <FloatingInput
          id="email"
          v-model="formData.email"
          label="Email"
          type="email"
          :disabled="isLoading"
          :required="true"
        />

        <!-- 密碼 -->
        <div class="password-group">
          <FloatingInput
            id="password"
            v-model="formData.password"
            label="密碼"
            type="password"
            :disabled="isLoading"
            :required="true"
          />
          <div class="password-strength">
            <div class="strength-bar" :class="passwordStrengthClass"></div>
          </div>
          <small class="hint">必須包含大小寫字母和數字，至少 8 個字元</small>
        </div>

        <!-- 確認密碼 -->
        <FloatingInput
          id="confirmPassword"
          v-model="formData.confirmPassword"
          label="確認密碼"
          type="password"
          :disabled="isLoading"
          :required="true"
          :error="passwordMismatchError"
        />

        <!-- 出生日期 -->
        <div class="date-group">
          <label for="dateOfBirth" class="date-label">出生日期</label>
          <input
            id="dateOfBirth"
            v-model="formData.date_of_birth"
            type="date"
            class="date-input"
            required
            :disabled="isLoading"
            :max="maxDate"
          />
          <small class="hint">必須年滿 18 歲</small>
        </div>

        <!-- 錯誤訊息 -->
        <div v-if="error" class="error-message">
          <span class="error-icon">⚠️</span>
          <span>{{ error }}</span>
        </div>

        <!-- 送出按鈕 -->
        <AnimatedButton
          type="submit"
          variant="secondary"
          :disabled="!isFormValid"
          :loading="isLoading"
        >
          <span v-if="!isLoading">🎉 註冊</span>
        </AnimatedButton>
      </form>

      <!-- 前往登入 -->
      <div class="auth-footer">
        <p>
          已有帳號？
          <router-link to="/login" class="login-link">立即登入 →</router-link>
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
import { useUserStore } from '@/stores/user'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import FloatingInput from '@/components/ui/FloatingInput.vue'

const router = useRouter()
const userStore = useUserStore()

// 表單資料
const formData = ref({
  email: '',
  password: '',
  confirmPassword: '',
  date_of_birth: '',
})

// 錯誤訊息
const error = ref('')

// 載入狀態
const isLoading = computed(() => userStore.isLoading)

// 計算 18 年前的日期（用於日期選擇器的最大值）
const maxDate = computed(() => {
  const date = new Date()
  date.setFullYear(date.getFullYear() - 18)
  return date.toISOString().split('T')[0]
})

// 密碼強度計算
const passwordStrength = computed(() => {
  const password = formData.value.password
  if (!password) return 0

  let strength = 0
  if (password.length >= 8) strength++
  if (/[A-Z]/.test(password)) strength++
  if (/[a-z]/.test(password)) strength++
  if (/\d/.test(password)) strength++
  if (/[^A-Za-z0-9]/.test(password)) strength++

  return strength
})

const passwordStrengthClass = computed(() => {
  const strength = passwordStrength.value
  if (strength <= 1) return 'weak'
  if (strength <= 3) return 'medium'
  return 'strong'
})

// 密碼不匹配錯誤
const passwordMismatchError = computed(() => {
  if (!formData.value.confirmPassword) return ''
  if (formData.value.password !== formData.value.confirmPassword) {
    return '密碼不一致'
  }
  return ''
})

// 表單驗證
const isFormValid = computed(() => {
  return (
    formData.value.email &&
    formData.value.password.length >= 8 &&
    formData.value.password === formData.value.confirmPassword &&
    formData.value.date_of_birth &&
    passwordStrength.value >= 3
  )
})

/**
 * 處理註冊
 */
const handleRegister = async () => {
  error.value = ''

  // 驗證密碼一致
  if (formData.value.password !== formData.value.confirmPassword) {
    error.value = '密碼不一致'
    return
  }

  // 驗證密碼強度
  const password = formData.value.password
  if (!/[A-Z]/.test(password)) {
    error.value = '密碼必須包含至少一個大寫字母'
    return
  }
  if (!/[a-z]/.test(password)) {
    error.value = '密碼必須包含至少一個小寫字母'
    return
  }
  if (!/\d/.test(password)) {
    error.value = '密碼必須包含至少一個數字'
    return
  }

  // 呼叫 API
  const success = await userStore.register({
    email: formData.value.email,
    password: formData.value.password,
    date_of_birth: formData.value.date_of_birth,
  })

  if (success) {
    // 註冊成功，導向首頁或驗證頁面
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
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
  right: -100px;
  animation-delay: 0s;
}

.circle-2 {
  width: 200px;
  height: 200px;
  bottom: -50px;
  left: -50px;
  animation-delay: 5s;
}

.circle-3 {
  width: 150px;
  height: 150px;
  top: 50%;
  left: 10%;
  animation-delay: 10s;
}

@keyframes float {
  0%, 100% {
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
  padding: 40px;
  max-width: 480px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3),
              0 0 0 1px rgba(255, 255, 255, 0.2);
  animation: slideUp 0.5s ease-out;
  max-height: 90vh;
  overflow-y: auto;
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
  margin-bottom: 32px;
}

.logo-animation {
  margin-bottom: 16px;
}

.logo-heart {
  display: inline-block;
  font-size: 3.5rem;
  animation: heartBeat 1.5s infinite;
  filter: drop-shadow(0 4px 8px rgba(245, 87, 108, 0.3));
}

@keyframes heartBeat {
  0%, 100% {
    transform: scale(1);
  }
  10%, 30% {
    transform: scale(1.1);
  }
  20%, 40% {
    transform: scale(0.9);
  }
}

.auth-header h1 {
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}

.auth-header p {
  color: #666;
  font-size: 0.95rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.password-group {
  margin-bottom: 16px;
}

.password-strength {
  width: 100%;
  height: 4px;
  background: #e0e0e0;
  border-radius: 2px;
  overflow: hidden;
  margin-top: -16px;
  margin-bottom: 4px;
}

.strength-bar {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 2px;
}

.strength-bar.weak {
  width: 33%;
  background: linear-gradient(90deg, #f44336, #e91e63);
}

.strength-bar.medium {
  width: 66%;
  background: linear-gradient(90deg, #ff9800, #ffc107);
}

.strength-bar.strong {
  width: 100%;
  background: linear-gradient(90deg, #4caf50, #66bb6a);
}

.hint {
  color: #999;
  font-size: 0.75rem;
  margin-top: -8px;
  display: block;
}

.date-group {
  margin-bottom: 16px;
}

.date-label {
  display: block;
  font-weight: 600;
  color: #333;
  font-size: 0.85rem;
  margin-bottom: 8px;
}

.date-input {
  width: 100%;
  padding: 14px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
  background: white;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
  font-family: inherit;
}

.date-input:focus {
  border-color: #f5576c;
  box-shadow: 0 0 0 4px rgba(245, 87, 108, 0.1);
}

.date-input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
  opacity: 0.7;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #fff5f5, #ffe5e5);
  color: #c33;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 0.9rem;
  border: 1px solid #ffcccc;
  animation: shake 0.5s ease;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-10px); }
  75% { transform: translateX(10px); }
}

.error-icon {
  font-size: 1.2rem;
}

.auth-footer {
  margin-top: 24px;
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.auth-footer p {
  color: #666;
  font-size: 0.9rem;
}

.login-link {
  color: #f5576c;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.login-link:hover {
  color: #f093fb;
  gap: 8px;
}

/* 自定義滾動條 */
.auth-card::-webkit-scrollbar {
  width: 6px;
}

.auth-card::-webkit-scrollbar-track {
  background: transparent;
}

.auth-card::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #f093fb, #f5576c);
  border-radius: 3px;
}

/* 響應式設計 */
@media (max-width: 480px) {
  .auth-card {
    padding: 32px 24px;
  }

  .auth-header h1 {
    font-size: 1.75rem;
  }

  .logo-heart {
    font-size: 3rem;
  }
}
</style>
