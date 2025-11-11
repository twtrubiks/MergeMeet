<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <h1>👋 歡迎回來</h1>
        <p>登入 MergeMeet</p>
      </div>

      <form @submit.prevent="handleLogin" class="auth-form">
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
            autocomplete="email"
          />
        </div>

        <!-- 密碼 -->
        <div class="form-group">
          <label for="password">密碼</label>
          <input
            id="password"
            v-model="formData.password"
            type="password"
            placeholder="輸入密碼"
            required
            :disabled="isLoading"
            autocomplete="current-password"
          />
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
          {{ isLoading ? '登入中...' : '登入' }}
        </button>
      </form>

      <!-- 前往註冊 -->
      <div class="auth-footer">
        <p>
          還沒有帳號？
          <router-link to="/register">立即註冊</router-link>
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
})

// 錯誤訊息
const error = ref('')

// 載入狀態
const isLoading = computed(() => userStore.isLoading)

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
    password: formData.value.password,
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
