<template>
  <div class="settings-container">
    <div class="settings-card">
      <div class="settings-header">
        <div class="logo-animation">
          <span class="logo-icon">&#x2699;</span>
        </div>
        <h1>帳號設定</h1>
        <p>管理您的帳號安全設定</p>
      </div>

      <!-- 密碼修改區塊 -->
      <div class="settings-section">
        <h2 class="section-title">
          <span class="section-icon">&#x1F512;</span>
          修改密碼
        </h2>

        <!-- 成功狀態 -->
        <div v-if="changeSuccess" class="success-state">
          <div class="success-icon">&#x2705;</div>
          <h3>密碼修改成功！</h3>
          <p class="success-text">已發送通知郵件到您的信箱</p>
          <p class="redirect-text">{{ redirectCountdown }} 秒後自動跳轉至登入頁...</p>
          <AnimatedButton variant="primary" @click="goToLogin" class="action-btn">
            立即登入
          </AnimatedButton>
        </div>

        <!-- 密碼修改表單 -->
        <form v-else @submit.prevent="handleChangePassword" class="password-form">
          <!-- 當前密碼 -->
          <FloatingInput
            id="current-password"
            v-model="formData.currentPassword"
            label="當前密碼"
            type="password"
            autocomplete="current-password"
            :disabled="isLoading"
            :required="true"
            :error="currentPasswordError"
          />

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

          <!-- 密碼強度指示器 -->
          <div v-if="formData.newPassword" class="password-strength">
            <span :class="{ valid: passwordStrength.length }">
              {{ passwordStrength.length ? '&#x2713;' : '&#x2717;' }} 至少 8 個字元
            </span>
            <span :class="{ valid: passwordStrength.uppercase }">
              {{ passwordStrength.uppercase ? '&#x2713;' : '&#x2717;' }} 包含大寫字母
            </span>
            <span :class="{ valid: passwordStrength.lowercase }">
              {{ passwordStrength.lowercase ? '&#x2713;' : '&#x2717;' }} 包含小寫字母
            </span>
            <span :class="{ valid: passwordStrength.number }">
              {{ passwordStrength.number ? '&#x2713;' : '&#x2717;' }} 包含數字
            </span>
          </div>

          <!-- 確認新密碼 -->
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

          <!-- 一般錯誤訊息 -->
          <p v-if="generalError" class="error-message">{{ generalError }}</p>

          <!-- 送出按鈕 -->
          <AnimatedButton
            type="submit"
            variant="primary"
            :disabled="!isFormValid || isLoading"
            :loading="isLoading"
          >
            <span v-if="!isLoading">&#x1F510; 修改密碼</span>
          </AnimatedButton>
        </form>
      </div>

      <!-- 返回首頁連結 -->
      <div class="settings-footer">
        <router-link to="/" class="back-link">&#x2190; 返回首頁</router-link>
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
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { authAPI } from '@/api/auth'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import FloatingInput from '@/components/ui/FloatingInput.vue'

const router = useRouter()
const userStore = useUserStore()

// 表單資料
const formData = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 狀態管理
const isLoading = ref(false)
const changeSuccess = ref(false)
const currentPasswordError = ref('')
const generalError = ref('')

// 倒計時
const redirectCountdown = ref(5)
let countdownTimer = null

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
    formData.value.currentPassword &&
    strength.length &&
    strength.uppercase &&
    strength.lowercase &&
    strength.number &&
    formData.value.newPassword === formData.value.confirmPassword
  )
})

// 處理密碼修改
const handleChangePassword = async () => {
  currentPasswordError.value = ''
  generalError.value = ''
  isLoading.value = true

  try {
    await authAPI.changePassword({
      current_password: formData.value.currentPassword,
      new_password: formData.value.newPassword
    })

    // 成功
    changeSuccess.value = true
    startRedirectCountdown()

  } catch (err) {
    const detail = err.response?.data?.detail || ''

    // 區分錯誤類型
    if (detail.includes('當前密碼錯誤')) {
      currentPasswordError.value = '當前密碼錯誤'
    } else if (detail.includes('不能與當前密碼相同')) {
      generalError.value = '新密碼不能與當前密碼相同'
    } else {
      generalError.value = detail || '修改失敗，請稍後再試'
    }

    console.error('修改密碼錯誤:', err)
  } finally {
    isLoading.value = false
  }
}

// 開始倒計時並自動跳轉
const startRedirectCountdown = () => {
  countdownTimer = setInterval(() => {
    redirectCountdown.value--
    if (redirectCountdown.value <= 0) {
      clearInterval(countdownTimer)
      goToLogin()
    }
  }, 1000)
}

// 導向登入頁
const goToLogin = () => {
  userStore.logout()
  router.push('/login')
}

// 清理定時器
onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
})
</script>

<style scoped>
.settings-container {
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

.settings-card {
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

.settings-header {
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

.settings-header h1 {
  font-size: 2.2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}

.settings-header p {
  color: #666;
  font-size: 1rem;
}

/* 區塊標題 */
.settings-section {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}

.section-icon {
  font-size: 1.4rem;
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

.success-state h3 {
  color: #4caf50;
  font-size: 1.8rem;
  margin-bottom: 16px;
  font-weight: 600;
}

.success-text {
  color: #666;
  margin-bottom: 8px;
  font-size: 1.1rem;
}

.redirect-text {
  color: #999;
  font-size: 0.95rem;
  margin-bottom: 24px;
}

.action-btn {
  margin-top: 16px;
}

/* 表單 */
.password-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
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

/* 頁尾 */
.settings-footer {
  margin-top: 32px;
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid #e0e0e0;
}

.back-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
}

.back-link:hover {
  color: #764ba2;
}

/* 響應式設計 */
@media (max-width: 480px) {
  .settings-card {
    padding: 32px 24px;
  }

  .settings-header h1 {
    font-size: 1.8rem;
  }

  .logo-icon,
  .success-icon {
    font-size: 3rem;
  }
}
</style>
