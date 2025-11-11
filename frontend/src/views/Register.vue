<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <h1>🎉 加入 MergeMeet</h1>
        <p>開始你的交友之旅</p>
      </div>

      <form @submit.prevent="handleRegister" class="auth-form">
        <!-- Email -->
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="formData.email"
            type="email"
            placeholder="your@example.com"
            required
            :disabled="isLoading"
          />
        </div>

        <!-- 密碼 -->
        <div class="form-group">
          <label for="password">密碼</label>
          <input
            id="password"
            v-model="formData.password"
            type="password"
            placeholder="至少 8 個字元"
            required
            :disabled="isLoading"
          />
          <small class="hint">必須包含大小寫字母和數字</small>
        </div>

        <!-- 確認密碼 -->
        <div class="form-group">
          <label for="confirmPassword">確認密碼</label>
          <input
            id="confirmPassword"
            v-model="formData.confirmPassword"
            type="password"
            placeholder="再次輸入密碼"
            required
            :disabled="isLoading"
          />
        </div>

        <!-- 出生日期 -->
        <div class="form-group">
          <label for="dateOfBirth">出生日期</label>
          <input
            id="dateOfBirth"
            v-model="formData.date_of_birth"
            type="date"
            required
            :disabled="isLoading"
            :max="maxDate"
          />
          <small class="hint">必須年滿 18 歲</small>
        </div>

        <!-- 錯誤訊息 -->
        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <!-- 送出按鈕 -->
        <button
          type="submit"
          class="btn-primary"
          :disabled="isLoading || !isFormValid"
        >
          {{ isLoading ? '註冊中...' : '註冊' }}
        </button>
      </form>

      <!-- 前往登入 -->
      <div class="auth-footer">
        <p>
          已有帳號？
          <router-link to="/login">立即登入</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

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

// 表單驗證
const isFormValid = computed(() => {
  return (
    formData.value.email &&
    formData.value.password.length >= 8 &&
    formData.value.password === formData.value.confirmPassword &&
    formData.value.date_of_birth
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
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.auth-card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  max-width: 450px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.auth-header {
  text-align: center;
  margin-bottom: 30px;
}

.auth-header h1 {
  font-size: 2rem;
  color: #333;
  margin-bottom: 8px;
}

.auth-header p {
  color: #666;
  font-size: 1rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.form-group input {
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.form-group input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.hint {
  color: #999;
  font-size: 0.85rem;
}

.error-message {
  background-color: #fee;
  color: #c33;
  padding: 12px;
  border-radius: 8px;
  font-size: 0.9rem;
  text-align: center;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 14px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-footer {
  margin-top: 24px;
  text-align: center;
}

.auth-footer p {
  color: #666;
  font-size: 0.9rem;
}

.auth-footer a {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
}

.auth-footer a:hover {
  text-decoration: underline;
}
</style>
