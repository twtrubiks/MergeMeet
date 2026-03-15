<template>
  <div class="settings-container">
    <div class="settings-card">
      <div class="settings-header">
        <div class="logo-animation">
          <Icon name="settings" size="xl" decorative />
        </div>
        <h1>帳號設定</h1>
        <p>管理您的帳號與配對偏好</p>
      </div>

      <!-- Tab 導航 -->
      <div class="settings-tabs">
        <n-tabs v-model:value="activeTab" type="line" animated>
          <!-- Tab 1: 配對設定（預設） -->
          <n-tab-pane name="matching">
            <template #tab>
              <span class="tab-label"><Icon name="heart" size="sm" decorative /> 配對設定</span>
            </template>
            <div class="tab-content">
              <!-- 載入中 -->
              <div v-if="preferenceLoading" class="loading-state">
                <div class="spinner"></div>
                <p>載入中...</p>
              </div>

              <!-- 偏好設定表單 -->
              <form v-else class="preference-form" @submit.prevent="handleSavePreferences">
                <!-- 年齡範圍 -->
                <div class="form-group">
                  <label class="form-label">年齡範圍</label>
                  <div class="age-range">
                    <div class="age-input">
                      <label>最小</label>
                      <input
                        v-model.number="preferences.minAge"
                        type="number"
                        min="18"
                        max="99"
                        :disabled="preferenceSaving"
                      />
                    </div>
                    <span class="range-separator">～</span>
                    <div class="age-input">
                      <label>最大</label>
                      <input
                        v-model.number="preferences.maxAge"
                        type="number"
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
                      v-model.number="preferences.maxDistance"
                      type="range"
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
                        v-model="preferences.genderPreference"
                        type="radio"
                        :value="option.value"
                        :disabled="preferenceSaving"
                      />
                      <span class="option-icon"
                        ><Icon :name="option.iconName" size="lg" decorative
                      /></span>
                      <span class="option-label">{{ option.label }}</span>
                    </label>
                  </div>
                </div>

                <!-- 錯誤訊息 -->
                <p v-if="preferenceError" class="error-message">{{ preferenceError }}</p>

                <!-- 成功訊息 -->
                <p v-if="preferenceSaveSuccess" class="success-message">
                  <Icon name="check-circle" size="sm" decorative /> 偏好設定已儲存
                </p>

                <!-- 儲存按鈕 -->
                <AnimatedButton
                  type="submit"
                  variant="primary"
                  :disabled="!isPreferenceValid || preferenceSaving"
                  :loading="preferenceSaving"
                >
                  <span v-if="!preferenceSaving"
                    ><Icon name="save" size="sm" decorative /> 儲存偏好</span
                  >
                </AnimatedButton>
              </form>
            </div>
          </n-tab-pane>

          <!-- Tab 2: 帳號安全 -->
          <n-tab-pane name="security">
            <template #tab>
              <span class="tab-label"><Icon name="shield" size="sm" decorative /> 帳號安全</span>
            </template>
            <div class="tab-content">
              <!-- 密碼修改區塊 -->
              <div class="settings-section">
                <h3 class="subsection-title">
                  <Icon name="lock" size="md" decorative />
                  修改密碼
                </h3>

                <!-- 成功狀態 -->
                <div v-if="changeSuccess" class="success-state">
                  <div class="success-icon"><Icon name="check-circle" size="xl" decorative /></div>
                  <h3>密碼修改成功！</h3>
                  <p class="success-text">已發送通知郵件到您的信箱</p>
                  <p class="redirect-text">{{ redirectCountdown }} 秒後自動跳轉至登入頁...</p>
                  <AnimatedButton variant="primary" class="action-btn" @click="goToLogin">
                    立即登入
                  </AnimatedButton>
                </div>

                <!-- 密碼修改表單 -->
                <form v-else class="password-form" @submit.prevent="handleChangePassword">
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
                    <span v-if="!isLoading"
                      ><Icon name="lock" size="sm" decorative /> 修改密碼</span
                    >
                  </AnimatedButton>
                </form>
              </div>

              <!-- 其他功能連結 -->
              <div class="settings-section quick-links">
                <h3 class="subsection-title">
                  <Icon name="clipboard" size="md" decorative />
                  其他功能
                </h3>
                <div class="link-list">
                  <router-link to="/my-reports" class="link-item">
                    <span class="link-icon"><Icon name="clipboard" size="md" decorative /></span>
                    <span class="link-text">我的舉報記錄</span>
                    <span class="link-arrow"
                      ><Icon name="back" size="sm" decorative class="arrow-icon"
                    /></span>
                  </router-link>
                  <router-link to="/blocked" class="link-item">
                    <span class="link-icon"><Icon name="shield" size="md" decorative /></span>
                    <span class="link-text">封鎖名單</span>
                    <span class="link-arrow"
                      ><Icon name="back" size="sm" decorative class="arrow-icon"
                    /></span>
                  </router-link>
                </div>
              </div>
            </div>
          </n-tab-pane>
        </n-tabs>
      </div>

      <!-- 返回首頁連結 -->
      <div class="settings-footer">
        <router-link to="/" class="back-link"
          ><Icon name="back" size="sm" decorative /> 返回首頁</router-link
        >
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
import { NTabs, NTabPane } from 'naive-ui'
import { useUserStore } from '@/stores/user'
import { useProfileStore } from '@/stores/profile'
import { authAPI } from '@/api/auth'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import FloatingInput from '@/components/ui/FloatingInput.vue'
import Icon from '@/components/ui/Icon.vue'
import { useFormDirty } from '@/composables/useFormDirty'

// Tab 狀態
const activeTab = ref('matching')

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

// 原始偏好設定（用於髒狀態檢測）
const originalPreferences = ref({
  minAge: 18,
  maxAge: 50,
  maxDistance: 50,
  genderPreference: 'all'
})

// 表單髒狀態追蹤
const { isDirty: isPreferencesDirty, setClean: setPreferencesClean } = useFormDirty(
  preferences,
  originalPreferences,
  {
    confirmMessage: '您的配對偏好有未儲存的變更，確定要離開嗎？'
  }
)

const preferenceLoading = ref(false)
const preferenceSaving = ref(false)
const preferenceError = ref('')
const preferenceSaveSuccess = ref(false)

// 性別選項
const genderOptions = [
  { value: 'male', label: '男性', iconName: 'male' },
  { value: 'female', label: '女性', iconName: 'female' },
  { value: 'both', label: '男女皆可', iconName: 'male-female' },
  { value: 'all', label: '不限', iconName: 'heart' }
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
  return (
    !ageRangeError.value &&
    preferences.value.minAge >= 18 &&
    preferences.value.maxAge <= 99 &&
    preferences.value.maxDistance >= 1 &&
    preferences.value.maxDistance <= 500
  )
})

// 載入偏好設定
const loadPreferences = async () => {
  preferenceLoading.value = true
  try {
    await profileStore.fetchProfile()
    if (profileStore.profile) {
      const loadedPrefs = {
        minAge: profileStore.profile.min_age_preference || 18,
        maxAge: profileStore.profile.max_age_preference || 50,
        maxDistance: profileStore.profile.max_distance_km || 50,
        genderPreference: profileStore.profile.gender_preference || 'all'
      }
      preferences.value = { ...loadedPrefs }
      // 儲存原始值用於髒狀態檢測
      originalPreferences.value = { ...loadedPrefs }
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
    // 標記表單為乾淨狀態
    setPreferencesClean()
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

.settings-card {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-xl);
  padding: var(--space-12);
  max-width: min(480px, calc(100vw - 40px));
  width: 100%;
  box-shadow: var(--shadow-xl);
  animation: slideUp var(--duration-slow) var(--easing-out);
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
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.settings-header h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  background: var(--color-primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: var(--space-2);
}

.settings-header p {
  color: #666;
  font-size: 1rem;
}

/* Tab 樣式 */
.settings-tabs {
  margin-top: 24px;
}

.settings-tabs :deep(.n-tabs-nav) {
  padding: 0 8px;
}

.settings-tabs :deep(.n-tabs-tab) {
  font-size: 1rem;
  font-weight: 600;
  padding: 12px 20px;
  transition: all 0.3s ease;
}

.settings-tabs :deep(.n-tabs-tab:hover) {
  color: var(--color-primary-600);
}

.settings-tabs :deep(.n-tabs-tab--active) {
  color: var(--color-primary-600);
}

.settings-tabs :deep(.n-tabs-bar) {
  background: var(--color-primary-gradient);
}

.tab-content {
  padding: 24px 0;
}

/* 子區塊標題 */
.subsection-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
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
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
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
  color: var(--color-text-muted);
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
  color: var(--color-primary-600);
  text-decoration: none;
  font-weight: var(--font-weight-semibold);
  transition: all var(--duration-slow) var(--easing-default);
}

.back-link:hover {
  color: var(--color-primary-700);
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
  border-color: var(--color-primary-600);
}

.age-input input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.range-separator {
  font-size: 1.5rem;
  color: var(--color-text-muted);
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

.distance-input input[type='range'] {
  flex: 1;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--color-primary-gradient);
  border-radius: var(--radius-sm);
  outline: none;
}

.distance-input input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 24px;
  height: 24px;
  background: white;
  border: 3px solid var(--color-primary-600);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: transform var(--duration-normal) var(--easing-default);
}

.distance-input input[type='range']::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.distance-input input[type='range']::-moz-range-thumb {
  width: 24px;
  height: 24px;
  background: white;
  border: 3px solid var(--color-primary-600);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

.distance-value {
  min-width: 80px;
  text-align: right;
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary-600);
}

.distance-marks {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--color-text-muted);
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
  border-color: var(--color-primary-600);
  background: var(--color-background);
}

.gender-option.active {
  border-color: var(--color-primary-600);
  background: var(--color-primary-alpha-10);
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
  margin: 0 auto var(--space-4);
  border: 4px solid var(--color-border-light);
  border-top: 4px solid var(--color-primary-600);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.loading-state p {
  color: #666;
  font-size: 0.95rem;
}

/* 快捷連結 */
.quick-links {
  margin-top: 24px;
}

.link-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.link-item {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background: #f8f9fa;
  border-radius: 12px;
  text-decoration: none;
  color: #333;
  transition: all 0.3s ease;
}

.link-item:hover {
  background: var(--color-primary-alpha-10);
  transform: translateX(4px);
}

.link-icon {
  font-size: 1.5rem;
  margin-right: 16px;
}

.link-text {
  flex: 1;
  font-weight: 500;
  font-size: 1rem;
}

.link-arrow {
  display: flex;
  align-items: center;
  color: var(--color-text-muted);
  transition: transform 0.3s ease;
}

.link-arrow .arrow-icon {
  transform: rotate(180deg);
}

.link-item:hover .link-arrow {
  transform: translateX(4px);
  color: var(--color-primary-600);
}

/* Tab 標籤樣式 */
.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* 響應式設計 */
@media (max-width: 480px) {
  .settings-container {
    padding: var(--space-3);
  }

  .settings-card {
    padding: var(--space-8) var(--space-6);
  }

  .settings-header h1 {
    font-size: var(--font-size-2xl);
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
    gap: var(--space-3);
  }

  .range-separator {
    display: none;
  }

  /* Ensure touch targets on mobile */
  .btn,
  .age-input input,
  select.form-control {
    min-height: var(--touch-target-min);
  }
}
</style>
