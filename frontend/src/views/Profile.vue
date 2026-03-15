<template>
  <div class="profile-page">
    <div class="container">
      <!-- 返回主選單按鈕 -->
      <router-link to="/" class="back-home-btn">
        <Icon name="home" size="sm" decorative />
        <span class="btn-text">返回主選單</span>
      </router-link>

      <!-- 載入中 -->
      <div v-if="profileStore.loading && !profileStore.profile" class="loading">
        <HeartLoader text="載入個人檔案..." />
      </div>

      <!-- 尚未建立檔案 -->
      <div v-else-if="!profileStore.hasProfile && !isCreating" class="empty-state">
        <div class="card">
          <div class="welcome-animation">
            <span class="welcome-heart">💕</span>
          </div>
          <h1>👋 歡迎！</h1>
          <p class="subtitle">建立你的個人檔案，開始認識新朋友</p>
          <AnimatedButton variant="primary" @click="startCreating">
            <Icon name="flash" size="sm" decorative /> 建立個人檔案
          </AnimatedButton>
        </div>
      </div>

      <!-- 建立/編輯檔案表單 -->
      <div v-else-if="isCreating || isEditing" class="profile-form">
        <div class="card">
          <h2>{{ isCreating ? '建立個人檔案' : '編輯個人檔案' }}</h2>

          <!-- 步驟指示器 -->
          <div class="steps">
            <div class="step" :class="{ active: currentStep === 1 }">
              <div class="step-number">1</div>
              <div class="step-label">基本資料</div>
            </div>
            <div class="step" :class="{ active: currentStep === 2 }">
              <div class="step-number">2</div>
              <div class="step-label">上傳照片</div>
            </div>
            <div class="step" :class="{ active: currentStep === 3 }">
              <div class="step-number">3</div>
              <div class="step-label">興趣標籤</div>
            </div>
          </div>

          <!-- 步驟 1: 基本資料 -->
          <div v-show="currentStep === 1" class="step-content">
            <div class="form-group">
              <label for="display_name">顯示名稱 *</label>
              <input
                id="display_name"
                v-model="formData.display_name"
                type="text"
                maxlength="100"
                placeholder="輸入你的名字或暱稱"
                required
              />
            </div>

            <div class="form-group">
              <label for="gender">性別 *</label>
              <select id="gender" v-model="formData.gender" required>
                <option value="">請選擇</option>
                <option value="male">男性</option>
                <option value="female">女性</option>
                <option value="non_binary">非二元性別</option>
                <option value="prefer_not_to_say">不願透露</option>
              </select>
            </div>

            <div class="form-group">
              <label for="bio">個人簡介 *</label>
              <textarea
                id="bio"
                v-model="formData.bio"
                maxlength="500"
                rows="4"
                placeholder="介紹一下自己吧..."
                required
              ></textarea>
              <small>{{ formData.bio?.length || 0 }} / 500</small>
            </div>

            <div class="form-group">
              <label for="location_name">地點 *</label>

              <!-- 自動定位按鈕 -->
              <div class="location-actions">
                <button
                  type="button"
                  class="btn-auto-location"
                  :disabled="gettingLocation"
                  @click="getAutoLocation"
                >
                  <span v-if="!gettingLocation"
                    ><Icon name="location" size="sm" decorative /> 自動獲取我的位置</span
                  >
                  <span v-else><Icon name="sync" size="sm" decorative /> 定位中...</span>
                </button>
                <small class="hint">或手動選擇城市</small>
              </div>

              <!-- 城市選擇下拉選單 -->
              <select id="location_name" v-model="formData.location_name" class="location-select">
                <option value="">請選擇城市</option>
                <optgroup label="北部">
                  <option value="台北市">台北市</option>
                  <option value="新北市">新北市</option>
                  <option value="基隆市">基隆市</option>
                  <option value="桃園市">桃園市</option>
                  <option value="新竹市">新竹市</option>
                  <option value="新竹縣">新竹縣</option>
                </optgroup>
                <optgroup label="中部">
                  <option value="苗栗縣">苗栗縣</option>
                  <option value="台中市">台中市</option>
                  <option value="彰化縣">彰化縣</option>
                  <option value="南投縣">南投縣</option>
                  <option value="雲林縣">雲林縣</option>
                </optgroup>
                <optgroup label="南部">
                  <option value="嘉義市">嘉義市</option>
                  <option value="嘉義縣">嘉義縣</option>
                  <option value="台南市">台南市</option>
                  <option value="高雄市">高雄市</option>
                  <option value="屏東縣">屏東縣</option>
                </optgroup>
                <optgroup label="東部">
                  <option value="宜蘭縣">宜蘭縣</option>
                  <option value="花蓮縣">花蓮縣</option>
                  <option value="台東縣">台東縣</option>
                </optgroup>
                <optgroup label="離島">
                  <option value="澎湖縣">澎湖縣</option>
                  <option value="金門縣">金門縣</option>
                  <option value="連江縣">連江縣（馬祖）</option>
                </optgroup>
              </select>

              <!-- 顯示座標信息（GPS 定位成功時） -->
              <small v-if="formData.gps_location" class="success-hint">
                <Icon name="check-circle" size="sm" decorative /> GPS 定位成功（已模糊化保護隱私）
              </small>
            </div>

            <div class="button-group">
              <AnimatedButton variant="ghost" @click="cancelEdit"> 取消 </AnimatedButton>
              <AnimatedButton variant="primary" @click="nextStep"> 下一步 → </AnimatedButton>
            </div>
          </div>

          <!-- 步驟 2: 上傳照片 -->
          <div v-show="currentStep === 2" class="step-content">
            <PhotoUploader @photos-changed="fetchProfileData" />

            <div class="button-group">
              <AnimatedButton variant="ghost" @click="currentStep = 1"> ← 上一步 </AnimatedButton>
              <AnimatedButton variant="primary" @click="nextStep"> 下一步 → </AnimatedButton>
            </div>
          </div>

          <!-- 步驟 3: 興趣標籤 -->
          <div v-show="currentStep === 3" class="step-content">
            <InterestSelector v-model="selectedInterests" />

            <div class="button-group">
              <AnimatedButton variant="ghost" @click="currentStep = 2"> ← 上一步 </AnimatedButton>
              <AnimatedButton
                variant="success"
                :disabled="profileStore.loading"
                :loading="profileStore.loading"
                @click="submitProfile"
              >
                <span v-if="!profileStore.loading"
                  ><Icon name="check" size="sm" decorative /> 完成</span
                >
              </AnimatedButton>
            </div>
          </div>

          <!-- 錯誤訊息 -->
          <div v-if="profileStore.error" class="error-message">
            {{ profileStore.error }}
          </div>
        </div>
      </div>

      <!-- 顯示檔案 -->
      <div v-else class="profile-view">
        <div class="card">
          <!-- 檔案頭部 -->
          <div class="profile-header">
            <div class="profile-avatar">
              <img
                v-if="profileStore.profilePicture"
                :src="profileStore.profilePicture"
                :alt="profileStore.profile.display_name"
              />
              <div v-else class="avatar-placeholder">
                {{ (profileStore.profile.display_name || 'U')[0].toUpperCase() }}
              </div>
            </div>
            <div class="profile-info">
              <h1>{{ profileStore.profile.display_name }}</h1>
              <p v-if="profileStore.profile.age" class="profile-age">
                {{ profileStore.profile.age }} 歲
              </p>
              <p v-if="profileStore.profile.location_name" class="profile-location">
                <Icon name="location" size="sm" decorative />
                {{ profileStore.profile.location_name }}
              </p>
            </div>
            <AnimatedButton variant="primary" @click="startEditing">
              <Icon name="edit" size="sm" decorative /> 編輯
            </AnimatedButton>
          </div>

          <!-- 個人簡介 -->
          <div class="profile-section">
            <h3>關於我</h3>
            <p class="bio">{{ profileStore.profile.bio }}</p>
          </div>

          <!-- 照片 -->
          <div v-if="profileStore.profilePhotos.length > 0" class="profile-section">
            <h3>照片 ({{ profileStore.profilePhotos.length }}/6)</h3>
            <div class="photo-grid">
              <div v-for="photo in profileStore.profilePhotos" :key="photo.id" class="photo-item">
                <img :src="photo.url" :alt="'Photo ' + photo.display_order" />
                <div v-if="photo.is_profile_picture" class="photo-badge">主頭像</div>
              </div>
            </div>
          </div>

          <!-- 興趣標籤 -->
          <div v-if="profileStore.profileInterests.length > 0" class="profile-section">
            <h3>興趣 ({{ profileStore.profileInterests.length }})</h3>
            <div class="interests-list">
              <span
                v-for="interest in profileStore.profileInterests"
                :key="interest.id"
                class="interest-tag"
              >
                {{ interest.icon }} {{ interest.name }}
              </span>
            </div>
          </div>

          <!-- 配對偏好 -->
          <div class="profile-section">
            <h3>配對偏好</h3>
            <div class="preferences">
              <div class="pref-item">
                <span class="pref-label">年齡範圍:</span>
                <span class="pref-value">
                  {{ profileStore.profile.min_age_preference }}-{{
                    profileStore.profile.max_age_preference
                  }}
                  歲
                </span>
              </div>
              <div class="pref-item">
                <span class="pref-label">距離:</span>
                <span class="pref-value">{{ profileStore.profile.max_distance_km }} 公里內</span>
              </div>
              <div class="pref-item">
                <span class="pref-label">性別偏好:</span>
                <span class="pref-value">{{
                  getGenderPreferenceText(profileStore.profile.gender_preference)
                }}</span>
              </div>
            </div>
          </div>

          <!-- 檔案狀態 -->
          <div class="profile-section">
            <div class="status-badges">
              <span
                class="badge"
                :class="profileStore.isProfileComplete ? 'badge-success' : 'badge-warning'"
              >
                <Icon
                  v-if="profileStore.isProfileComplete"
                  name="check-circle"
                  size="sm"
                  decorative
                />
                <Icon v-else name="warning" size="sm" decorative />
                {{ profileStore.isProfileComplete ? '檔案完整' : '檔案不完整' }}
              </span>
              <span
                class="badge"
                :class="profileStore.profile.is_visible ? 'badge-success' : 'badge-inactive'"
              >
                <Icon v-if="profileStore.profile.is_visible" name="eye" size="sm" decorative />
                <Icon v-else name="lock" size="sm" decorative />
                {{ profileStore.profile.is_visible ? '公開' : '隱藏' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProfileStore } from '@/stores/profile'
import { useUserStore } from '@/stores/user'
import PhotoUploader from '@/components/PhotoUploader.vue'
import InterestSelector from '@/components/InterestSelector.vue'
import AnimatedButton from '@/components/ui/AnimatedButton.vue'
import HeartLoader from '@/components/ui/HeartLoader.vue'
import Icon from '@/components/ui/Icon.vue'
import { useFormDirty } from '@/composables/useFormDirty'
import { useMessage, useDialog } from 'naive-ui'
import { logger } from '@/utils/logger'

const router = useRouter()
const profileStore = useProfileStore()
const userStore = useUserStore()
const message = useMessage()
const dialog = useDialog()

// 表單狀態
const isCreating = ref(false)
const isEditing = ref(false)
const currentStep = ref(1)
const gettingLocation = ref(false)

// 表單資料
const formData = ref({
  display_name: '',
  gender: '',
  bio: '',
  location_name: '',
  gps_location: null // 存儲 GPS 定位結果 { latitude, longitude }
})

// 原始表單資料（用於髒狀態檢測）
const originalFormData = ref({
  display_name: '',
  gender: '',
  bio: '',
  location_name: '',
  gps_location: null
})

// 選擇的興趣標籤
const selectedInterests = ref([])

// 表單髒狀態追蹤（僅在編輯模式下啟用）
const isFormActive = computed(() => isCreating.value || isEditing.value)
const { isDirty, setClean } = useFormDirty(formData, originalFormData, {
  confirmMessage: '您的個人檔案有未儲存的變更，確定要離開嗎？',
  // 只有在編輯/建立模式下才啟用確認
  confirmOnLeave: true
})

/**
 * 開始建立檔案
 */
const startCreating = () => {
  isCreating.value = true
  currentStep.value = 1
  resetFormData()
}

/**
 * 開始編輯檔案
 */
const startEditing = () => {
  isEditing.value = true
  currentStep.value = 1
  // 填充現有資料
  const existingData = {
    display_name: profileStore.profile.display_name,
    gender: profileStore.profile.gender,
    bio: profileStore.profile.bio,
    location_name: profileStore.profile.location_name || '',
    gps_location: null
  }
  formData.value = { ...existingData }
  // 儲存原始資料用於髒狀態檢測
  originalFormData.value = { ...existingData }
  selectedInterests.value = profileStore.profileInterests.map((i) => i.id)
}

/**
 * 取消編輯
 */
const cancelEdit = () => {
  isCreating.value = false
  isEditing.value = false
  currentStep.value = 1
  resetFormData()
}

/**
 * 重置表單資料
 */
const resetFormData = () => {
  formData.value = {
    display_name: '',
    gender: '',
    bio: '',
    location_name: ''
  }
  selectedInterests.value = []
}

/**
 * 下一步
 */
const nextStep = async () => {
  // 驗證步驟 1
  if (currentStep.value === 1) {
    if (!formData.value.display_name || !formData.value.gender || !formData.value.bio) {
      message.warning('請填寫所有必填欄位')
      return
    }
    // 如果是建立模式，先儲存基本資料
    if (isCreating.value) {
      await saveBasicInfo()
      // 如果建立失敗，不繼續下一步
      if (!profileStore.profile) {
        return
      }
      // 建立成功後直接進入下一步
      currentStep.value++
      return
    }
  }

  // 驗證步驟 2（可選提示）
  if (currentStep.value === 2) {
    if (profileStore.profilePhotos.length === 0) {
      // 使用 Promise 包裝 dialog 調用
      return new Promise((resolve) => {
        dialog.warning({
          title: '提醒',
          content: '建議至少上傳 1 張照片以提高配對成功率，確定要跳過嗎？',
          positiveText: '繼續',
          negativeText: '返回',
          onPositiveClick: () => {
            currentStep.value++
            resolve()
          }
        })
      })
    }
  }

  // 驗證步驟 3
  if (currentStep.value === 3) {
    if (selectedInterests.value.length < 3 || selectedInterests.value.length > 10) {
      message.warning('請選擇 3-10 個興趣標籤')
      return
    }
  }

  // 只有在步驟 2 沒有返回 Promise 時才前進到下一步
  if (currentStep.value !== 2 || profileStore.profilePhotos.length > 0) {
    currentStep.value++
  }
}

/**
 * 位置模糊化（保護隱私）
 * 添加 500m-1km 隨機偏移，避免洩漏精確位置
 */
const fuzzyLocation = (latitude, longitude) => {
  // 添加 0.005 度隨機偏移（約 500m-1km）
  const offset = 0.005
  const randomLat = latitude + (Math.random() - 0.5) * offset
  const randomLng = longitude + (Math.random() - 0.5) * offset

  // 保留 4 位小數（約 10m 精度）
  return {
    latitude: Math.round(randomLat * 10000) / 10000,
    longitude: Math.round(randomLng * 10000) / 10000
  }
}

/**
 * 自動獲取用戶位置（使用瀏覽器 Geolocation API）
 */
const getAutoLocation = async () => {
  if (!navigator.geolocation) {
    message.warning('您的瀏覽器不支援定位功能，請手動選擇城市')
    return
  }

  gettingLocation.value = true

  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true, // 高精度定位
        timeout: 10000, // 10 秒超時
        maximumAge: 0 // 不使用快取位置
      })
    })

    const { latitude, longitude } = position.coords

    // 位置模糊化保護隱私
    const fuzzyCoords = fuzzyLocation(latitude, longitude)

    // 存儲 GPS 座標
    formData.value.gps_location = fuzzyCoords

    // 反向地理編碼（簡化版：根據座標判斷大概城市）
    const cityName = getCityFromCoords(latitude, longitude)
    if (cityName) {
      formData.value.location_name = cityName
    }

    message.success('✅ 定位成功！已自動獲取您的位置')
    logger.log('GPS location obtained:', fuzzyCoords)
  } catch (error) {
    logger.error('定位失敗:', error)

    // 根據錯誤類型顯示不同訊息
    if (error.code === 1) {
      message.warning('您拒絕了定位權限，請手動選擇城市')
    } else if (error.code === 2) {
      message.error('無法獲取位置，請檢查 GPS 或網路連接')
    } else if (error.code === 3) {
      message.warning('定位超時，請手動選擇城市')
    } else {
      message.warning('定位失敗，請手動選擇城市')
    }
  } finally {
    gettingLocation.value = false
  }
}

/**
 * 根據座標判斷城市（簡化版反向地理編碼）
 */
const getCityFromCoords = (lat, lng) => {
  // 台灣主要城市的大概範圍（簡化判斷）
  const cityRanges = [
    { name: '台北市', lat: [24.95, 25.25], lng: [121.45, 121.65] },
    { name: '新北市', lat: [24.8, 25.3], lng: [121.3, 122.0] },
    { name: '基隆市', lat: [25.08, 25.18], lng: [121.68, 121.8] },
    { name: '桃園市', lat: [24.8, 25.1], lng: [120.9, 121.5] },
    { name: '新竹市', lat: [24.75, 24.85], lng: [120.9, 121.0] },
    { name: '台中市', lat: [24.0, 24.3], lng: [120.5, 120.9] },
    { name: '台南市', lat: [22.9, 23.1], lng: [120.1, 120.35] },
    { name: '高雄市', lat: [22.5, 22.8], lng: [120.2, 120.45] }
  ]

  for (const city of cityRanges) {
    if (lat >= city.lat[0] && lat <= city.lat[1] && lng >= city.lng[0] && lng <= city.lng[1]) {
      return city.name
    }
  }

  return '台灣' // 預設值
}

/**
 * 將地點名稱轉換為經緯度（擴展版）
 */
const geocodeLocation = (locationName) => {
  // 輸入驗證
  if (!locationName || typeof locationName !== 'string') {
    logger.warn('地點名稱無效')
    return null
  }

  // 長度限制
  if (locationName.length > 50) {
    logger.warn('地點名稱過長')
    return null
  }

  // 只允許中文、英文、數字和常見符號
  const validPattern = /^[\u4e00-\u9fa5a-zA-Z0-9\s-]+$/
  if (!validPattern.test(locationName)) {
    logger.warn('地點名稱包含無效字符')
    return null
  }

  // 台灣所有縣市的經緯度（城市中心點座標）
  const cityCoordinates = {
    // 北部
    台北市: { latitude: 25.033, longitude: 121.5654 },
    新北市: { latitude: 25.012, longitude: 121.4659 },
    基隆市: { latitude: 25.1276, longitude: 121.7392 },
    桃園市: { latitude: 24.9936, longitude: 121.301 },
    新竹市: { latitude: 24.8138, longitude: 120.9675 },
    新竹縣: { latitude: 24.8387, longitude: 121.0177 },
    // 中部
    苗栗縣: { latitude: 24.5602, longitude: 120.8214 },
    台中市: { latitude: 24.1477, longitude: 120.6736 },
    彰化縣: { latitude: 24.0518, longitude: 120.5161 },
    南投縣: { latitude: 23.9609, longitude: 120.9719 },
    雲林縣: { latitude: 23.7092, longitude: 120.4313 },
    // 南部
    嘉義市: { latitude: 23.48, longitude: 120.4491 },
    嘉義縣: { latitude: 23.4518, longitude: 120.2554 },
    台南市: { latitude: 22.9997, longitude: 120.227 },
    高雄市: { latitude: 22.6273, longitude: 120.3014 },
    屏東縣: { latitude: 22.5519, longitude: 120.5487 },
    // 東部
    宜蘭縣: { latitude: 24.7021, longitude: 121.7378 },
    花蓮縣: { latitude: 23.9871, longitude: 121.6015 },
    台東縣: { latitude: 22.7583, longitude: 121.1444 },
    // 離島
    澎湖縣: { latitude: 23.5712, longitude: 119.5793 },
    金門縣: { latitude: 24.4324, longitude: 118.317 },
    連江縣: { latitude: 26.1605, longitude: 119.9515 } // 馬祖
  }

  // 直接匹配完整地點名稱
  const coords = cityCoordinates[locationName]

  if (!coords) {
    logger.warn(`未找到城市座標: ${locationName}`)
    return null
  }

  return coords
}

/**
 * 將 formData 中的位置欄位（gps_location / location_name）
 * 轉換為 API 所需的 location 物件，並清理臨時欄位。
 * @returns 處理後的 profileData，若地點無法識別則回傳 null
 */
const resolveLocationData = (profileData) => {
  // 優先使用 GPS 定位座標（更精確）
  if (profileData.gps_location) {
    profileData.location = {
      latitude: profileData.gps_location.latitude,
      longitude: profileData.gps_location.longitude,
      location_name: profileData.location_name || '台灣'
    }
    delete profileData.gps_location
    delete profileData.location_name
  }
  // 降級：使用城市中心座標
  else if (profileData.location_name) {
    const coords = geocodeLocation(profileData.location_name)
    if (!coords) {
      return null
    }
    profileData.location = {
      latitude: coords.latitude,
      longitude: coords.longitude,
      location_name: profileData.location_name
    }
    delete profileData.location_name
  }
  return profileData
}

/**
 * 儲存基本資料
 */
const saveBasicInfo = async () => {
  try {
    const profileData = resolveLocationData({ ...formData.value })
    if (!profileData) {
      message.error('無法識別該地點，請選擇有效的城市')
      return
    }

    await profileStore.createProfile(profileData)
    // 只有成功後才切換狀態
    isCreating.value = false
    isEditing.value = true
    setClean() // 標記表單為乾淨狀態
    message.success('個人檔案創建成功')
  } catch (error) {
    logger.error('建立個人檔案失敗:', error)
    message.error('創建失敗，請檢查網絡連接')
    // 不改變狀態，讓用戶可以重試
  }
}

/**
 * 提交完整檔案
 */
const submitProfile = async () => {
  try {
    // 更新基本資料（如果有修改）
    if (isEditing.value) {
      const profileData = resolveLocationData({ ...formData.value })
      if (!profileData) {
        message.error('無法識別該地點，請選擇有效的城市')
        return
      }

      await profileStore.updateProfile(profileData)
    }

    // 更新興趣標籤
    if (selectedInterests.value.length >= 3 && selectedInterests.value.length <= 10) {
      await profileStore.updateInterests(selectedInterests.value)
    }

    // 完成
    isCreating.value = false
    isEditing.value = false
    currentStep.value = 1
    setClean() // 標記表單為乾淨狀態

    // 重新載入檔案
    await fetchProfileData()
  } catch (error) {
    logger.error('儲存檔案失敗:', error)
  }
}

/**
 * 取得檔案資料
 */
const fetchProfileData = async () => {
  try {
    await profileStore.fetchProfile()
  } catch (error) {
    logger.error('取得檔案失敗:', error)
  }
}

/**
 * 取得性別偏好文字
 */
const getGenderPreferenceText = (preference) => {
  const map = {
    male: '男性',
    female: '女性',
    both: '不限',
    all: '所有人'
  }
  return map[preference] || '未設定'
}

// 初始化
onMounted(async () => {
  // 檢查登入狀態
  if (!userStore.isAuthenticated) {
    router.push('/login')
    return
  }

  // 取得檔案
  await fetchProfileData()

  // 取得興趣標籤
  await profileStore.fetchInterestTags()
})
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.container {
  max-width: 800px;
  margin: 0 auto;
}

/* 返回主選單按鈕 */
.back-home-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.95);
  color: #667eea;
  text-decoration: none;
  border-radius: 25px;
  font-weight: 600;
  font-size: 0.95rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  margin-bottom: 20px;
}

.back-home-btn:hover {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
}

.back-home-btn .btn-icon {
  font-size: 1.2rem;
}

.back-home-btn .btn-text {
  font-size: 0.95rem;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

/* 載入中 */
.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 100px 20px;
}

/* 空狀態 */
.empty-state {
  text-align: center;
  animation: fadeIn 0.6s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.welcome-animation {
  margin-bottom: 24px;
}

.welcome-heart {
  display: inline-block;
  font-size: 5rem;
  animation: heartBeat 1.5s infinite;
  filter: drop-shadow(0 8px 16px rgba(255, 107, 107, 0.4));
}

@keyframes heartBeat {
  0%,
  100% {
    transform: scale(1);
  }
  10%,
  30% {
    transform: scale(1.15);
  }
  20%,
  40% {
    transform: scale(0.95);
  }
}

.empty-state h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  font-weight: 800;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  color: #666;
  font-size: 1.2rem;
  margin-bottom: 2rem;
  font-weight: 500;
}

/* 步驟指示器 */
.steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid #f0f0f0;
  position: relative;
}

.steps::before {
  content: '';
  position: absolute;
  top: 20px;
  left: 20%;
  right: 20%;
  height: 2px;
  background: #e0e0e0;
  z-index: 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  opacity: 0.4;
  transition: all 0.4s ease;
  position: relative;
  z-index: 1;
}

.step.active {
  opacity: 1;
  transform: scale(1.05);
}

.step-number {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.step.active .step-number {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  transform: scale(1.1);
}

.step-label {
  font-size: 0.95rem;
  color: #666;
  font-weight: 600;
}

.step.active .step-label {
  color: #667eea;
}

/* 表單 */
.form-group {
  margin-bottom: 1.75rem;
}

.form-group label {
  display: block;
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: #333;
  font-size: 0.95rem;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 14px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: white;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  transform: translateY(-2px);
}

.form-group textarea {
  resize: vertical;
  min-height: 120px;
  font-family: inherit;
}

.form-group select {
  cursor: pointer;
}

.form-group small {
  display: block;
  margin-top: 0.5rem;
  color: var(--color-text-muted);
  font-size: 0.85rem;
  font-weight: 500;
}

.form-group .hint {
  color: var(--color-text-muted);
  font-style: italic;
  font-weight: 400;
}

.form-group .success-hint {
  color: #4caf50;
  font-weight: 500;
  margin-top: 8px;
  display: block;
}

/* 位置相關樣式 */
.location-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.btn-auto-location {
  padding: 12px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.btn-auto-location:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-auto-location:active:not(:disabled) {
  transform: translateY(0);
}

.btn-auto-location:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.location-select {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 15px;
  transition: all 0.3s ease;
  background: white;
  cursor: pointer;
}

.location-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.location-select option {
  padding: 8px;
}

.location-select optgroup {
  font-weight: 600;
  color: #667eea;
}

/* 按鈕 */
.button-group {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.error-message {
  margin-top: 1.5rem;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(244, 67, 54, 0.1), rgba(233, 30, 99, 0.1));
  border: 2px solid rgba(244, 67, 54, 0.3);
  border-radius: 12px;
  color: #c33;
  font-weight: 600;
  animation: shake 0.5s ease;
}

@keyframes shake {
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-10px);
  }
  75% {
    transform: translateX(10px);
  }
}

/* 檔案顯示 */
.profile-header {
  display: flex;
  align-items: center;
  gap: 2rem;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid #f0f0f0;
  position: relative;
}

.profile-avatar {
  flex-shrink: 0;
  position: relative;
}

.profile-avatar img,
.avatar-placeholder {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  object-fit: cover;
  border: 4px solid white;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.avatar-placeholder {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 3rem;
  font-weight: 800;
}

.profile-info {
  flex: 1;
}

.profile-info h1 {
  margin: 0 0 0.75rem 0;
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.profile-age,
.profile-location {
  margin: 0.5rem 0;
  color: #666;
  font-size: 1.05rem;
  font-weight: 500;
}

.profile-section {
  margin-bottom: 2.5rem;
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.profile-section h3 {
  margin-bottom: 1.25rem;
  font-size: 1.3rem;
  font-weight: 800;
  color: #333;
}

.bio {
  color: #666;
  line-height: 1.8;
  font-size: 1.05rem;
  font-weight: 400;
}

/* 照片網格 */
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1.25rem;
}

.photo-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.photo-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.photo-item:hover img {
  transform: scale(1.05);
}

.photo-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 700;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

/* 興趣標籤 */
.interests-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.interest-tag {
  padding: 10px 18px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 20px;
  font-size: 0.95rem;
  color: #667eea;
  font-weight: 600;
  transition: all 0.2s ease;
}

.interest-tag:hover {
  transform: scale(1.05);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
}

/* 偏好設定 */
.preferences {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.pref-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
  border-radius: 12px;
  border: 1px solid rgba(102, 126, 234, 0.15);
  transition: all 0.2s ease;
}

.pref-item:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
  transform: translateX(4px);
}

.pref-label {
  font-weight: 700;
  color: #666;
  font-size: 0.95rem;
}

.pref-value {
  color: #333;
  font-weight: 600;
  font-size: 0.95rem;
}

/* 狀態標籤 */
.status-badges {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.badge {
  padding: 10px 18px;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 700;
  transition: all 0.2s ease;
}

.badge:hover {
  transform: scale(1.05);
}

.badge-success {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.15), rgba(102, 187, 106, 0.15));
  color: #2e7d32;
  border: 2px solid rgba(76, 175, 80, 0.3);
}

.badge-warning {
  background: linear-gradient(135deg, rgba(255, 152, 0, 0.15), rgba(255, 193, 7, 0.15));
  color: #e65100;
  border: 2px solid rgba(255, 152, 0, 0.3);
}

.badge-inactive {
  background: rgba(0, 0, 0, 0.05);
  color: #666;
  border: 2px solid rgba(0, 0, 0, 0.1);
}

/* 響應式 */
@media (max-width: 768px) {
  .card {
    padding: 1.5rem;
  }

  .profile-header {
    flex-direction: column;
    text-align: center;
    gap: 1.5rem;
  }

  .profile-avatar img,
  .avatar-placeholder {
    width: 100px;
    height: 100px;
  }

  .avatar-placeholder {
    font-size: 2.5rem;
  }

  .profile-info h1 {
    font-size: 1.75rem;
  }

  .steps {
    flex-direction: column;
    gap: 1.5rem;
  }

  .steps::before {
    display: none;
  }

  .step-number {
    width: 45px;
    height: 45px;
    font-size: 1rem;
  }

  .button-group {
    flex-direction: column;
  }

  .photo-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  .status-badges {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .profile-page {
    padding: 16px;
  }

  .card {
    padding: 1.25rem;
    border-radius: 12px;
  }

  .empty-state h1 {
    font-size: 2rem;
  }

  .subtitle {
    font-size: 1rem;
  }

  .welcome-heart {
    font-size: 4rem;
  }

  .profile-section h3 {
    font-size: 1.1rem;
  }

  .photo-grid {
    grid-template-columns: 1fr;
  }
}
</style>
