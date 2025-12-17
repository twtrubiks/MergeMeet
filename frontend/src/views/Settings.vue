<template>
  <div class="settings-container">
    <div class="settings-card">
      <div class="settings-header">
        <div class="logo-animation">
          <span class="logo-icon">&#x2699;</span>
        </div>
        <h1>帳號設定</h1>
        <p>管理您的帳號與配對偏好</p>
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

      <!-- 配對偏好設定區塊 -->
      <div class="settings-section">
        <h2 class="section-title">
          <span class="section-icon">&#x1F495;</span>
          配對偏好
        </h2>

        <!-- 載入中 -->
        <div v-if="preferenceLoading" class="loading-state">
          <div class="spinner"></div>
          <p>載入中...</p>
        </div>

        <!-- 偏好設定表單 -->
        <form v-else @submit.prevent="handleSavePreferences" class="preference-form">
          <!-- 年齡範圍 -->
          <div class="form-group">
            <label class="form-label">年齡範圍</label>
            <div class="age-range">
              <div class="age-input">
                <label>最小</label>
                <input
                  type="number"
                  v-model.number="preferences.minAge"
                  min="18"
                  max="99"
                  :disabled="preferenceSaving"
                />
              </div>
              <span class="range-separator">～</span>
              <div class="age-input">
                <label>最大</label>
                <input
                  type="number"
                  v-model.number="preferences.maxAge"
                  min="18"
                  max="99"
                  :disabled="preferenceSaving"
                />
              </div>
            </div>
            <p v-if="ageRangeError" class="field-error">{{ ageRangeError }}</p>
          </div>

          <!-- 最大距離 -->
          <div class="form-group">
            <label class="form-label">最大距離</label>
            <div class="distance-input">
              <input
                type="range"
                v-model.number="preferences.maxDistance"
                min="1"
                max="500"
                :disabled="preferenceSaving"
              />
              <span class="distance-value">{{ preferences.maxDistance }} 公里</span>
            </div>
            <div class="distance-marks">
              <span>1km</span>
              <span>100km</span>
              <span>250km</span>
              <span>500km</span>
            </div>
          </div>

          <!-- 性別偏好 -->
          <div class="form-group">
            <label class="form-label">性別偏好</label>
            <div class="gender-options">
              <label
                v-for="option in genderOptions"
                :key="option.value"
                class="gender-option"
                :class="{ active: preferences.genderPreference === option.value }"
              >
                <input
                  type="radio"
                  v-model="preferences.genderPreference"
                  :value="option.value"
                  :disabled="preferenceSaving"
                />
                <span class="option-icon">{{ option.icon }}</span>
                <span class="option-label">{{ option.label }}</span>
              </label>
            </div>
          </div>

          <!-- 錯誤訊息 -->
          <p v-if="preferenceError" class="error-message">{{ preferenceError }}</p>

          <!-- 成功訊息 -->
          <p v-if="preferenceSaveSuccess" class="success-message">&#x2705; 偏好設定已儲存</p>

          <!-- 儲存按鈕 -->
          <AnimatedButton
            type="submit"
            variant="primary"
            :disabled="!isPreferenceValid || preferenceSaving"
            :loading="preferenceSaving"
          >
            <span v-if="!preferenceSaving">&#x1F4BE; 儲存偏好</span>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useProfileStore } from '@/stores/profile'
import { authAPI } from '@/api/auth'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import FloatingInput from '@/components/ui/FloatingInput.vue'

const router = useRouter()
const userStore = useUserStore()
const profileStore = useProfileStore()

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

// ==================== 配對偏好設定 ====================

// 偏好設定狀態
const preferences = ref({
  minAge: 18,
  maxAge: 50,
  maxDistance: 50,
  genderPreference: 'all'
})

const preferenceLoading = ref(false)
const preferenceSaving = ref(false)
const preferenceError = ref('')
const preferenceSaveSuccess = ref(false)

// 性別選項
const genderOptions = [
  { value: 'male', label: '男性', icon: '👨' },
  { value: 'female', label: '女性', icon: '👩' },
  { value: 'both', label: '男女皆可', icon: '👫' },
  { value: 'all', label: '不限', icon: '🌈' }
]

// 年齡範圍驗證
const ageRangeError = computed(() => {
  if (preferences.value.minAge > preferences.value.maxAge) {
    return '最小年齡不能大於最大年齡'
  }
  if (preferences.value.minAge < 18 || preferences.value.maxAge > 99) {
    return '年齡範圍必須在 18-99 歲之間'
  }
  return ''
})

// 偏好設定驗證
const isPreferenceValid = computed(() => {
  return !ageRangeError.value &&
    preferences.value.minAge >= 18 &&
    preferences.value.maxAge <= 99 &&
    preferences.value.maxDistance >= 1 &&
    preferences.value.maxDistance <= 500
})

// 載入偏好設定
const loadPreferences = async () => {
  preferenceLoading.value = true
  try {
    await profileStore.fetchProfile()
    if (profileStore.profile) {
      preferences.value = {
        minAge: profileStore.profile.min_age_preference || 18,
        maxAge: profileStore.profile.max_age_preference || 50,
        maxDistance: profileStore.profile.max_distance_km || 50,
        genderPreference: profileStore.profile.gender_preference || 'all'
      }
    }
  } catch (err) {
    preferenceError.value = '載入偏好設定失敗'
    console.error('載入偏好設定錯誤:', err)
  } finally {
    preferenceLoading.value = false
  }
}

// 儲存偏好設定
const handleSavePreferences = async () => {
  if (!isPreferenceValid.value) return

  preferenceError.value = ''
  preferenceSaveSuccess.value = false
  preferenceSaving.value = true

  try {
    await profileStore.updateProfile({
      min_age_preference: preferences.value.minAge,
      max_age_preference: preferences.value.maxAge,
      max_distance_km: preferences.value.maxDistance,
      gender_preference: preferences.value.genderPreference
    })

    preferenceSaveSuccess.value = true
    // 3 秒後隱藏成功訊息
    setTimeout(() => {
      preferenceSaveSuccess.value = false
    }, 3000)
  } catch (err) {
    preferenceError.value = err.response?.data?.detail || '儲存失敗，請稍後再試'
    console.error('儲存偏好設定錯誤:', err)
  } finally {
    preferenceSaving.value = false
  }
}

// 頁面載入時取得偏好設定
onMounted(() => {
  loadPreferences()
})

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

/* 配對偏好設定 */
.preference-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}

/* 年齡範圍 */
.age-range {
  display: flex;
  align-items: center;
  gap: 16px;
}

.age-input {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.age-input label {
  font-size: 0.8rem;
  color: #666;
}

.age-input input {
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
  text-align: center;
  transition: border-color 0.3s ease;
}

.age-input input:focus {
  outline: none;
  border-color: #667eea;
}

.age-input input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.range-separator {
  font-size: 1.5rem;
  color: #999;
  padding-top: 20px;
}

.field-error {
  color: #e53935;
  font-size: 0.85rem;
  margin: 0;
}

/* 距離滑桿 */
.distance-input {
  display: flex;
  align-items: center;
  gap: 16px;
}

.distance-input input[type="range"] {
  flex: 1;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: linear-gradient(to right, #667eea, #764ba2);
  border-radius: 4px;
  outline: none;
}

.distance-input input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 24px;
  height: 24px;
  background: white;
  border: 3px solid #667eea;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease;
}

.distance-input input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.distance-input input[type="range"]::-moz-range-thumb {
  width: 24px;
  height: 24px;
  background: white;
  border: 3px solid #667eea;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.distance-value {
  min-width: 80px;
  text-align: right;
  font-weight: 600;
  color: #667eea;
}

.distance-marks {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #999;
  padding: 0 4px;
}

/* 性別選項 */
.gender-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.gender-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
}

.gender-option:hover {
  border-color: #667eea;
  background: #f8f8ff;
}

.gender-option.active {
  border-color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
}

.gender-option input {
  display: none;
}

.option-icon {
  font-size: 2rem;
}

.option-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
}

/* 成功訊息 */
.success-message {
  color: #4caf50;
  font-size: 0.9rem;
  text-align: center;
  padding: 12px;
  background: #e8f5e9;
  border-radius: 8px;
  margin: 0;
}

/* 載入狀態 */
.loading-state {
  text-align: center;
  padding: 40px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 16px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-state p {
  color: #666;
  font-size: 0.95rem;
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

  .gender-options {
    grid-template-columns: 1fr;
  }

  .age-range {
    flex-direction: column;
    gap: 12px;
  }

  .range-separator {
    display: none;
  }
}
</style>
