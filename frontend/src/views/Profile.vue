<template>
  <div class="profile-page">
    <div class="container">
      <!-- 載入中 -->
      <div v-if="profileStore.loading && !profileStore.profile" class="loading">
        <div class="spinner"></div>
        <p>載入中...</p>
      </div>

      <!-- 尚未建立檔案 -->
      <div v-else-if="!profileStore.hasProfile && !isCreating" class="empty-state">
        <div class="card">
          <h1>👋 歡迎！</h1>
          <p class="subtitle">建立你的個人檔案，開始認識新朋友</p>
          <button @click="startCreating" class="btn-primary">建立個人檔案</button>
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
              <label for="location_name">地點</label>
              <input
                id="location_name"
                v-model="formData.location_name"
                type="text"
                placeholder="例如：台北市"
              />
              <small class="hint">暫不支援自動定位，請手動輸入</small>
            </div>

            <div class="button-group">
              <button @click="cancelEdit" class="btn-secondary">取消</button>
              <button @click="nextStep" class="btn-primary">下一步</button>
            </div>
          </div>

          <!-- 步驟 2: 上傳照片 -->
          <div v-show="currentStep === 2" class="step-content">
            <PhotoUploader @photos-changed="fetchProfileData" />

            <div class="button-group">
              <button @click="currentStep = 1" class="btn-secondary">上一步</button>
              <button @click="nextStep" class="btn-primary">下一步</button>
            </div>
          </div>

          <!-- 步驟 3: 興趣標籤 -->
          <div v-show="currentStep === 3" class="step-content">
            <InterestSelector v-model="selectedInterests" />

            <div class="button-group">
              <button @click="currentStep = 2" class="btn-secondary">上一步</button>
              <button
                @click="submitProfile"
                class="btn-primary"
                :disabled="profileStore.loading"
              >
                {{ profileStore.loading ? '儲存中...' : '完成' }}
              </button>
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
                {{ profileStore.profile.display_name?.[0]?.toUpperCase() }}
              </div>
            </div>
            <div class="profile-info">
              <h1>{{ profileStore.profile.display_name }}</h1>
              <p class="profile-age" v-if="profileStore.profile.age">
                {{ profileStore.profile.age }} 歲
              </p>
              <p class="profile-location" v-if="profileStore.profile.location_name">
                📍 {{ profileStore.profile.location_name }}
              </p>
            </div>
            <button @click="startEditing" class="btn-edit">編輯</button>
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
              <div
                v-for="photo in profileStore.profilePhotos"
                :key="photo.id"
                class="photo-item"
              >
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
                  {{ profileStore.profile.min_age_preference }}-{{ profileStore.profile.max_age_preference }} 歲
                </span>
              </div>
              <div class="pref-item">
                <span class="pref-label">距離:</span>
                <span class="pref-value">{{ profileStore.profile.max_distance_km }} 公里內</span>
              </div>
              <div class="pref-item">
                <span class="pref-label">性別偏好:</span>
                <span class="pref-value">{{ getGenderPreferenceText(profileStore.profile.gender_preference) }}</span>
              </div>
            </div>
          </div>

          <!-- 檔案狀態 -->
          <div class="profile-section">
            <div class="status-badges">
              <span class="badge" :class="profileStore.isProfileComplete ? 'badge-success' : 'badge-warning'">
                {{ profileStore.isProfileComplete ? '✅ 檔案完整' : '⚠️ 檔案不完整' }}
              </span>
              <span class="badge" :class="profileStore.profile.is_visible ? 'badge-success' : 'badge-inactive'">
                {{ profileStore.profile.is_visible ? '👁️ 公開' : '🔒 隱藏' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useProfileStore } from '@/stores/profile'
import { useUserStore } from '@/stores/user'
import PhotoUploader from '@/components/PhotoUploader.vue'
import InterestSelector from '@/components/InterestSelector.vue'

const router = useRouter()
const profileStore = useProfileStore()
const userStore = useUserStore()

// 表單狀態
const isCreating = ref(false)
const isEditing = ref(false)
const currentStep = ref(1)

// 表單資料
const formData = ref({
  display_name: '',
  gender: '',
  bio: '',
  location_name: ''
})

// 選擇的興趣標籤
const selectedInterests = ref([])

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
  formData.value = {
    display_name: profileStore.profile.display_name,
    gender: profileStore.profile.gender,
    bio: profileStore.profile.bio,
    location_name: profileStore.profile.location_name || ''
  }
  selectedInterests.value = profileStore.profileInterests.map(i => i.id)
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
      alert('請填寫所有必填欄位')
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
      const confirmed = confirm('建議至少上傳 1 張照片以提高配對成功率，確定要跳過嗎？')
      if (!confirmed) {
        return
      }
    }
  }

  // 驗證步驟 3
  if (currentStep.value === 3) {
    if (selectedInterests.value.length < 3 || selectedInterests.value.length > 10) {
      alert('請選擇 3-10 個興趣標籤')
      return
    }
  }

  currentStep.value++
}

/**
 * 將地點名稱轉換為經緯度（簡易版）
 */
const geocodeLocation = (locationName) => {
  // 常見台灣城市的經緯度（僅供測試使用）
  const cityCoordinates = {
    '台北市': { latitude: 25.0330, longitude: 121.5654 },
    '新北市': { latitude: 25.0120, longitude: 121.4659 },
    '桃園市': { latitude: 24.9936, longitude: 121.3010 },
    '台中市': { latitude: 24.1477, longitude: 120.6736 },
    '台南市': { latitude: 22.9997, longitude: 120.2270 },
    '高雄市': { latitude: 22.6273, longitude: 120.3014 },
    '新竹市': { latitude: 24.8138, longitude: 120.9675 },
    '基隆市': { latitude: 25.1276, longitude: 121.7392 },
  }

  // 查找匹配的城市
  for (const [city, coords] of Object.entries(cityCoordinates)) {
    if (locationName.includes(city)) {
      return coords
    }
  }

  // 如果找不到，返回台北市座標作為預設
  return { latitude: 25.0330, longitude: 121.5654 }
}

/**
 * 儲存基本資料
 */
const saveBasicInfo = async () => {
  try {
    // 如果有填寫地點，轉換為經緯度
    const profileData = { ...formData.value }
    if (profileData.location_name) {
      const coords = geocodeLocation(profileData.location_name)
      profileData.location = {
        latitude: coords.latitude,
        longitude: coords.longitude,
        location_name: profileData.location_name
      }
      delete profileData.location_name // 移除純文字欄位
    }

    await profileStore.createProfile(profileData)
    isCreating.value = false
    isEditing.value = true // 切換到編輯模式
  } catch (error) {
    console.error('建立檔案失敗:', error)
  }
}

/**
 * 提交完整檔案
 */
const submitProfile = async () => {
  try {
    // 更新基本資料（如果有修改）
    if (isEditing.value) {
      // 如果有填寫地點，轉換為經緯度
      const profileData = { ...formData.value }
      if (profileData.location_name) {
        const coords = geocodeLocation(profileData.location_name)
        profileData.location = {
          latitude: coords.latitude,
          longitude: coords.longitude,
          location_name: profileData.location_name
        }
        delete profileData.location_name // 移除純文字欄位
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

    // 重新載入檔案
    await fetchProfileData()
  } catch (error) {
    console.error('儲存檔案失敗:', error)
  }
}

/**
 * 取得檔案資料
 */
const fetchProfileData = async () => {
  try {
    await profileStore.fetchProfile()
  } catch (error) {
    console.error('取得檔案失敗:', error)
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

.card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

/* 載入中 */
.loading {
  text-align: center;
  color: white;
  padding: 4rem 0;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 空狀態 */
.empty-state {
  text-align: center;
}

.empty-state h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  color: #333;
}

.subtitle {
  color: #666;
  font-size: 1.2rem;
  margin-bottom: 2rem;
}

/* 步驟指示器 */
.steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid #f0f0f0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  opacity: 0.5;
  transition: opacity 0.3s;
}

.step.active {
  opacity: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.step.active .step-number {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.step-label {
  font-size: 0.9rem;
  color: #666;
}

/* 表單 */
.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #333;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-group small {
  display: block;
  margin-top: 0.5rem;
  color: #999;
  font-size: 0.85rem;
}

.form-group .hint {
  color: #999;
  font-style: italic;
}

/* 按鈕 */
.button-group {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.btn-primary,
.btn-secondary,
.btn-edit {
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  font-size: 1rem;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
  transform: translateY(-2px);
}

.btn-edit {
  background: #667eea;
  color: white;
  padding: 8px 16px;
  font-size: 0.9rem;
}

.error-message {
  margin-top: 1rem;
  padding: 12px;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c33;
}

/* 檔案顯示 */
.profile-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid #f0f0f0;
}

.profile-avatar {
  flex-shrink: 0;
}

.profile-avatar img,
.avatar-placeholder {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-placeholder {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  font-weight: 600;
}

.profile-info {
  flex: 1;
}

.profile-info h1 {
  margin: 0 0 0.5rem 0;
  color: #333;
}

.profile-age,
.profile-location {
  margin: 0.25rem 0;
  color: #666;
}

.profile-section {
  margin-bottom: 2rem;
}

.profile-section h3 {
  margin-bottom: 1rem;
  color: #333;
}

.bio {
  color: #666;
  line-height: 1.6;
}

/* 照片網格 */
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
}

.photo-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 12px;
  overflow: hidden;
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(102, 126, 234, 0.9);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

/* 興趣標籤 */
.interests-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.interest-tag {
  padding: 8px 16px;
  background: #f0f0f0;
  border-radius: 20px;
  font-size: 0.9rem;
  color: #333;
}

/* 偏好設定 */
.preferences {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.pref-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.pref-label {
  font-weight: 600;
  color: #666;
}

.pref-value {
  color: #333;
}

/* 狀態標籤 */
.status-badges {
  display: flex;
  gap: 1rem;
}

.badge {
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge-success {
  background: #d4edda;
  color: #155724;
}

.badge-warning {
  background: #fff3cd;
  color: #856404;
}

.badge-inactive {
  background: #f0f0f0;
  color: #666;
}

/* 響應式 */
@media (max-width: 768px) {
  .profile-header {
    flex-direction: column;
    text-align: center;
  }

  .steps {
    flex-direction: column;
    gap: 1rem;
  }

  .button-group {
    flex-direction: column;
  }

  .photo-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
