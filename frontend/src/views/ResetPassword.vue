<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <div class="logo-animation">
          <span class="logo-icon">🔒</span>
        </div>
        <h1>重置密碼</h1>
        <p v-if="!verifying && tokenValid">設定您的新密碼</p>
      </div>

      <!-- 載入中 - 驗證 Token -->
      <div v-if="verifying" class="loading-state">
        <div class="spinner"></div>
        <p>驗證重置鏈接中...</p>
      </div>

      <!-- Token 無效 -->
      <div v-else-if="!tokenValid" class="error-state">
        <div class="error-icon">❌</div>
        <h2>鏈接無效</h2>
        <p class="error-text">{{ tokenError }}</p>
        <AnimatedButton
          variant="primary"
          @click="goToForgotPassword"
          class="action-btn"
        >
          重新申請
        </AnimatedButton>
        <div class="auth-footer">
          <p>
            <router-link to="/login" class="login-link">返回登入</router-link>
          </p>
        </div>
      </div>

      <!-- 成功狀態 -->
      <div v-else-if="resetSuccess" class="success-state">
        <div class="success-icon">✅</div>
        <h2>密碼重置成功！</h2>
        <p class="success-text">您的密碼已更新，請使用新密碼登入。</p>
        <AnimatedButton
          variant="primary"
          @click="goToLogin"
          class="action-btn"
        >
          前往登入
        </AnimatedButton>
      </div>

      <!-- 重置表單 -->
      <form v-else @submit.prevent="handleSubmit" class="auth-form">
        <p v-if="userEmail" class="user-info">
          正在為 <strong>{{ userEmail }}</strong> 重置密碼
        </p>

        <!-- 新密碼 -->
        <FloatingInput
          id="new-password"
          v-model="formData.newPassword"
          label="新密碼"
          type="password"
          autocomplete="new-password"
          :disabled="isLoading"
          :required="true"
        />

        <!-- 密碼強度提示 -->
        <div v-if="formData.newPassword" class="password-strength">
          <span :class="{ valid: passwordStrength.length }">
            {{ passwordStrength.length ? '✓' : '✗' }} 至少 8 個字元
          </span>
          <span :class="{ valid: passwordStrength.uppercase }">
            {{ passwordStrength.uppercase ? '✓' : '✗' }} 包含大寫字母
          </span>
          <span :class="{ valid: passwordStrength.lowercase }">
            {{ passwordStrength.lowercase ? '✓' : '✗' }} 包含小寫字母
          </span>
          <span :class="{ valid: passwordStrength.number }">
            {{ passwordStrength.number ? '✓' : '✗' }} 包含數字
          </span>
        </div>

        <!-- 確認密碼 -->
        <FloatingInput
          id="confirm-password"
          v-model="formData.confirmPassword"
          label="確認新密碼"
          type="password"
          autocomplete="new-password"
          :disabled="isLoading"
          :required="true"
          :error="passwordMismatchError"
        />

        <!-- 錯誤訊息 -->
        <p v-if="error" class="error-message">{{ error }}</p>

        <!-- 送出按鈕 -->
        <AnimatedButton
          type="submit"
          variant="primary"
          :disabled="!isFormValid || isLoading"
          :loading="isLoading"
        >
          <span v-if="!isLoading">🔐 重置密碼</span>
        </AnimatedButton>
      </form>
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiClient from '@/api/client'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import FloatingInput from '@/components/ui/FloatingInput.vue'

const route = useRoute()
const router = useRouter()

// 表單資料
const formData = ref({
  newPassword: '',
  confirmPassword: ''
})

// 狀態管理
const isLoading = ref(false)
const error = ref('')
const verifying = ref(true)
const tokenValid = ref(false)
const tokenError = ref('')
const resetSuccess = ref(false)
const userEmail = ref('')

// Token 從 URL 獲取
const token = computed(() => route.query.token)

// 計算密碼強度
const passwordStrength = computed(() => {
  const pwd = formData.value.newPassword
  if (!pwd) return { length: false, uppercase: false, lowercase: false, number: false }

  return {
    length: pwd.length >= 8,
    uppercase: /[A-Z]/.test(pwd),
    lowercase: /[a-z]/.test(pwd),
    number: /\d/.test(pwd)
  }
})

// 密碼不一致錯誤
const passwordMismatchError = computed(() => {
  if (!formData.value.confirmPassword) return ''
  if (formData.value.newPassword !== formData.value.confirmPassword) {
    return '兩次密碼輸入不一致'
  }
  return ''
})

// 表單驗證
const isFormValid = computed(() => {
  const strength = passwordStrength.value
  return (
    strength.length &&
    strength.uppercase &&
    strength.lowercase &&
    strength.number &&
    formData.value.newPassword === formData.value.confirmPassword
  )
})

// 驗證 Token
const verifyToken = async () => {
  if (!token.value) {
    verifying.value = false
    tokenValid.value = false
    tokenError.value = '無效的重置鏈接，請重新申請'
    return
  }

  try {
    // API 呼叫 - 無尾隨斜線
    const response = await apiClient.get('/auth/verify-reset-token', {
      params: { token: token.value }
    })

    if (response.data.valid) {
      tokenValid.value = true
      userEmail.value = response.data.email
    } else {
      tokenValid.value = false
      tokenError.value = '重置鏈接無效或已過期'
    }
  } catch (err) {
    tokenValid.value = false
    tokenError.value = err.response?.data?.detail || '重置鏈接無效或已過期'
    console.error('Token 驗證錯誤:', err)
  } finally {
    verifying.value = false
  }
}

// 提交重置密碼
const handleSubmit = async () => {
  error.value = ''
  isLoading.value = true

  try {
    // API 呼叫 - 無尾隨斜線
    await apiClient.post('/auth/reset-password', {
      token: token.value,
      new_password: formData.value.newPassword
    })

    // 重置成功
    resetSuccess.value = true
  } catch (err) {
    error.value = err.response?.data?.detail || '重置失敗，請稍後再試'
    console.error('重置密碼錯誤:', err)
  } finally {
    isLoading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}

const goToForgotPassword = () => {
  router.push('/forgot-password')
}

// 頁面載入時驗證 Token
onMounted(() => {
  verifyToken()
})
</script>

<style scoped>
.auth-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  padding: 48px;
  max-width: 480px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3),
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
  filter: drop-shadow(0 4px 8px rgba(102, 126, 234, 0.3));
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.auth-header h1 {
  font-size: 2.2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}

.auth-header p {
  color: #666;
  font-size: 1rem;
}

/* 載入狀態 */
.loading-state {
  text-align: center;
  padding: 40px 0;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  color: #666;
  font-size: 1rem;
}

/* 錯誤狀態 */
.error-state {
  text-align: center;
  padding: 20px 0;
}

.error-icon {
  font-size: 4rem;
  margin-bottom: 20px;
  animation: shake 0.5s ease-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-10px); }
  75% { transform: translateX(10px); }
}

.error-state h2 {
  color: #e53935;
  font-size: 1.6rem;
  margin-bottom: 16px;
  font-weight: 600;
}

.error-text {
  color: #666;
  margin-bottom: 24px;
  line-height: 1.6;
}

/* 成功狀態 */
.success-state {
  text-align: center;
  padding: 20px 0;
}

.success-icon {
  font-size: 4rem;
  margin-bottom: 20px;
  animation: bounce 0.6s ease-out;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.success-state h2 {
  color: #4caf50;
  font-size: 1.8rem;
  margin-bottom: 16px;
  font-weight: 600;
}

.success-text {
  color: #666;
  margin-bottom: 24px;
  font-size: 1.1rem;
}

.action-btn {
  margin-top: 16px;
}

/* 表單 */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-info {
  color: #666;
  text-align: center;
  margin-bottom: 16px;
  font-size: 0.95rem;
}

.user-info strong {
  color: #667eea;
}

/* 密碼強度指示器 */
.password-strength {
  margin-top: 8px;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.password-strength span {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e53935;
  transition: color 0.3s ease;
}

.password-strength span.valid {
  color: #4caf50;
}

.password-strength span::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
}

.error-message {
  color: #e53935;
  font-size: 0.9rem;
  text-align: center;
  padding: 12px;
  background: #ffebee;
  border-radius: 8px;
  margin-top: 8px;
}

.auth-footer {
  margin-top: 32px;
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid #e0e0e0;
}

.auth-footer p {
  color: #666;
  font-size: 0.95rem;
}

.login-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
}

.login-link:hover {
  color: #764ba2;
}

/* 響應式設計 */
@media (max-width: 480px) {
  .auth-card {
    padding: 32px 24px;
  }

  .auth-header h1 {
    font-size: 1.8rem;
  }

  .logo-icon,
  .error-icon,
  .success-icon {
    font-size: 3rem;
  }
}
</style>
