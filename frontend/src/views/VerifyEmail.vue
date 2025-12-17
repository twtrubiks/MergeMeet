<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <div class="logo-animation">
          <span class="logo-icon">📧</span>
        </div>
        <h1>驗證您的 Email</h1>
        <p>我們已發送驗證碼至</p>
        <p class="email-display">{{ userEmail }}</p>
      </div>

      <!-- 驗證成功狀態 -->
      <div v-if="verifySuccess" class="success-state">
        <div class="success-icon">✅</div>
        <h2>驗證成功！</h2>
        <p class="success-text">正在前往個人資料頁面...</p>
      </div>

      <!-- 驗證碼輸入表單 -->
      <form v-else @submit.prevent="handleVerify" class="auth-form">
        <p class="instruction">請輸入 6 位數驗證碼</p>

        <!-- 6 位數驗證碼輸入框 -->
        <div class="code-inputs">
          <input
            v-for="i in 6"
            :key="i"
            :ref="el => { if (el) codeInputs[i-1] = el }"
            type="text"
            inputmode="numeric"
            maxlength="1"
            v-model="codeDigits[i-1]"
            @input="handleCodeInput(i-1, $event)"
            @keydown="handleKeyDown(i-1, $event)"
            @paste="handlePaste"
            @focus="handleFocus(i-1)"
            :disabled="isLoading"
            class="code-input"
            :class="{ 'has-value': codeDigits[i-1] }"
          />
        </div>

        <!-- 錯誤訊息 -->
        <p v-if="error" class="error-message">{{ error }}</p>

        <!-- 驗證按鈕 -->
        <AnimatedButton
          type="submit"
          variant="primary"
          :disabled="!isCodeComplete || isLoading"
          :loading="isLoading"
        >
          <span v-if="!isLoading">驗證 Email</span>
        </AnimatedButton>

        <!-- 重新發送區塊 -->
        <div class="resend-section">
          <p v-if="cooldownSeconds > 0" class="cooldown-text">
            {{ cooldownSeconds }} 秒後可重新發送
          </p>
          <button
            v-else
            type="button"
            @click="handleResend"
            :disabled="isResending"
            class="resend-btn"
          >
            {{ isResending ? '發送中...' : '重新發送驗證碼' }}
          </button>
          <p v-if="resendSuccess" class="resend-success">
            驗證碼已重新發送，請查收郵件
          </p>
        </div>

        <!-- 提示 -->
        <div class="hint-section">
          <p class="hint-text">沒有收到郵件？請檢查垃圾郵件資料夾</p>
        </div>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'

const router = useRouter()
const userStore = useUserStore()

// 驗證碼相關
const codeDigits = ref(['', '', '', '', '', ''])
const codeInputs = ref([])

// 狀態
const isLoading = ref(false)
const isResending = ref(false)
const error = ref('')
const verifySuccess = ref(false)
const resendSuccess = ref(false)

// 60 秒冷卻倒計時
const cooldownSeconds = ref(0)
let cooldownTimer = null

// 計算屬性
const userEmail = computed(() => userStore.user?.email || '您的郵箱')
const isCodeComplete = computed(() =>
  codeDigits.value.every(d => d !== '')
)
const verificationCode = computed(() =>
  codeDigits.value.join('')
)

// 處理驗證碼輸入
const handleCodeInput = (index, event) => {
  const value = event.target.value.replace(/\D/g, '')
  codeDigits.value[index] = value

  // 自動聚焦下一個輸入框
  if (value && index < 5) {
    codeInputs.value[index + 1]?.focus()
  }
}

// 處理鍵盤事件
const handleKeyDown = (index, event) => {
  // Backspace 時聚焦前一個輸入框
  if (event.key === 'Backspace' && !codeDigits.value[index] && index > 0) {
    codeInputs.value[index - 1]?.focus()
  }

  // 左箭頭
  if (event.key === 'ArrowLeft' && index > 0) {
    codeInputs.value[index - 1]?.focus()
  }

  // 右箭頭
  if (event.key === 'ArrowRight' && index < 5) {
    codeInputs.value[index + 1]?.focus()
  }
}

// 處理貼上
const handlePaste = (event) => {
  event.preventDefault()
  const pastedData = event.clipboardData.getData('text').replace(/\D/g, '')

  for (let i = 0; i < Math.min(pastedData.length, 6); i++) {
    codeDigits.value[i] = pastedData[i]
  }

  // 聚焦到最後一個填入的輸入框或第六個
  const lastIndex = Math.min(pastedData.length - 1, 5)
  if (lastIndex >= 0) {
    codeInputs.value[lastIndex]?.focus()
  }
}

// 處理聚焦
const handleFocus = (index) => {
  // 選中當前輸入框的內容
  codeInputs.value[index]?.select()
}

// 處理驗證
const handleVerify = async () => {
  if (!isCodeComplete.value || isLoading.value) return

  error.value = ''
  isLoading.value = true

  try {
    const success = await userStore.verifyEmail(verificationCode.value)

    if (success) {
      verifySuccess.value = true
      // 2 秒後導向個人資料頁
      setTimeout(() => {
        router.push('/profile')
      }, 2000)
    } else {
      error.value = userStore.error || '驗證失敗，請檢查驗證碼'
      // 清空驗證碼輸入
      codeDigits.value = ['', '', '', '', '', '']
      codeInputs.value[0]?.focus()
    }
  } finally {
    isLoading.value = false
  }
}

// 啟動冷卻倒計時
const startCooldown = () => {
  cooldownSeconds.value = 60
  cooldownTimer = setInterval(() => {
    cooldownSeconds.value--
    if (cooldownSeconds.value <= 0) {
      clearInterval(cooldownTimer)
    }
  }, 1000)
}

// 處理重新發送
const handleResend = async () => {
  if (cooldownSeconds.value > 0 || isResending.value) return

  isResending.value = true
  resendSuccess.value = false
  error.value = ''

  try {
    const success = await userStore.resendVerification()

    if (success) {
      resendSuccess.value = true
      startCooldown()

      // 3 秒後隱藏成功訊息
      setTimeout(() => {
        resendSuccess.value = false
      }, 3000)
    } else {
      error.value = userStore.error || '重新發送失敗'
    }
  } finally {
    isResending.value = false
  }
}

// 生命週期
onMounted(() => {
  // 檢查用戶是否已登入
  if (!userStore.isAuthenticated) {
    router.push('/login')
    return
  }

  // 檢查是否已驗證
  if (userStore.user?.email_verified) {
    router.push('/profile')
    return
  }

  // 自動聚焦第一個輸入框
  setTimeout(() => {
    codeInputs.value[0]?.focus()
  }, 100)
})

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})
</script>

<style scoped>
.auth-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
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
  margin-bottom: 32px;
}

.logo-animation {
  margin-bottom: 20px;
}

.logo-icon {
  display: inline-block;
  font-size: 4rem;
  animation: pulse 2s infinite;
  filter: drop-shadow(0 4px 8px rgba(17, 153, 142, 0.3));
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
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
}

.auth-header p {
  color: #666;
  font-size: 0.95rem;
  margin: 4px 0;
}

.email-display {
  color: #11998e !important;
  font-weight: 600;
  font-size: 1.1rem !important;
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
  font-size: 1.1rem;
}

/* 表單 */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.instruction {
  text-align: center;
  color: #666;
  font-size: 0.95rem;
  margin-bottom: 8px;
}

/* 驗證碼輸入框 */
.code-inputs {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.code-input {
  width: 52px;
  height: 60px;
  text-align: center;
  font-size: 1.8rem;
  font-weight: 600;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: #fafafa;
  color: #333;
  transition: all 0.3s ease;
  outline: none;
}

.code-input:focus {
  border-color: #11998e;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(17, 153, 142, 0.15);
}

.code-input.has-value {
  border-color: #38ef7d;
  background: #fff;
}

.code-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 錯誤訊息 */
.error-message {
  color: #e53935;
  font-size: 0.9rem;
  text-align: center;
  padding: 12px;
  background: #ffebee;
  border-radius: 8px;
}

/* 重新發送區塊 */
.resend-section {
  text-align: center;
  margin-top: 8px;
}

.cooldown-text {
  color: #999;
  font-size: 0.9rem;
}

.resend-btn {
  background: none;
  border: none;
  color: #11998e;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.resend-btn:hover:not(:disabled) {
  background: rgba(17, 153, 142, 0.1);
}

.resend-btn:disabled {
  color: #999;
  cursor: not-allowed;
}

.resend-success {
  color: #4caf50;
  font-size: 0.9rem;
  margin-top: 8px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 提示區塊 */
.hint-section {
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid #e0e0e0;
}

.hint-text {
  color: #999;
  font-size: 0.85rem;
}

/* 響應式設計 */
@media (max-width: 480px) {
  .auth-card {
    padding: 32px 24px;
  }

  .auth-header h1 {
    font-size: 1.6rem;
  }

  .logo-icon,
  .success-icon {
    font-size: 3rem;
  }

  .code-inputs {
    gap: 8px;
  }

  .code-input {
    width: 44px;
    height: 52px;
    font-size: 1.5rem;
  }
}
</style>
