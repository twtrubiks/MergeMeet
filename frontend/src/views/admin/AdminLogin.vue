<template>
  <div class="admin-login-page">
    <div class="login-container">
      <div class="login-header">
        <h1>MergeMeet 管理後台</h1>
        <p>管理員登入</p>
      </div>

      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="top"
        require-mark-placement="right-hanging"
      >
        <n-form-item label="Email" path="email">
          <n-input
            v-model:value="formData.email"
            placeholder="請輸入管理員 Email"
            type="text"
            @keydown.enter="handleLogin"
          />
        </n-form-item>

        <n-form-item label="密碼" path="password">
          <n-input
            v-model:value="formData.password"
            placeholder="請輸入密碼"
            type="password"
            show-password-on="click"
            @keydown.enter="handleLogin"
          />
        </n-form-item>

        <n-button
          type="primary"
          block
          size="large"
          :loading="loading"
          @click="handleLogin"
        >
          登入管理後台
        </n-button>
      </n-form>

      <div class="login-footer">
        <n-button text @click="() => $router.push('/login')">
          一般用戶登入
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import apiClient from '@/api/client'
import { useUserStore } from '@/stores/user'
import { logger } from '@/utils/logger'

const router = useRouter()
const message = useMessage()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const formData = ref({
  email: '',
  password: ''
})

const rules = {
  email: [
    { required: true, message: '請輸入 Email', trigger: 'blur' },
    { type: 'email', message: '請輸入有效的 Email', trigger: ['blur', 'input'] }
  ],
  password: [
    { required: true, message: '請輸入密碼', trigger: 'blur' },
    { min: 6, message: '密碼至少 6 個字元', trigger: ['blur', 'input'] }
  ]
}

const handleLogin = async () => {
  try {
    await formRef.value?.validate()

    loading.value = true

    // 調用管理員登入 API
    const response = await apiClient.post('/auth/admin-login', {
      email: formData.value.email,
      password: formData.value.password
    })

    // 儲存 token
    userStore.saveTokens({
      access_token: response.data.access_token,
      refresh_token: response.data.refresh_token
    })

    // 設置用戶資訊（標記為管理員）
    userStore.user = {
      email: formData.value.email,
      is_admin: true
    }

    // 初始化用戶狀態
    userStore.initializeFromToken()

    message.success('登入成功')
    router.push('/admin')
  } catch (error) {
    logger.error('登入失敗:', error)
    message.error(error.response?.data?.detail || '登入失敗')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-container {
  background: white;
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  margin-bottom: 8px;
}

.login-header p {
  font-size: 16px;
  color: #666;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
}
</style>
