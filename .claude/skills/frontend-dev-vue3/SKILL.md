---
name: frontend-dev-vue3
description: 在 MergeMeet 開發前端功能時使用此 skill。提供 Vue 3 Composition API + Pinia + Vue Router 的開發模式指南，包含組件設計、狀態管理、路由、API 整合和 WebSocket 處理。
---

# Vue 3 前端開發指南

## 目的

建立 MergeMeet 專案中 Vue 3 + Pinia + Vue Router 開發的一致模式。

---

## 專案結構

```
frontend/
├── src/
│   ├── components/             # 可重用 Vue 組件
│   │   ├── InterestSelector.vue
│   │   ├── MatchModal.vue
│   │   ├── PhotoUploader.vue
│   │   ├── ReportModal.vue
│   │   ├── NotificationBell.vue
│   │   ├── UserDetailModal.vue
│   │   ├── chat/               # 聊天相關組件
│   │   │   ├── MessageBubble.vue
│   │   │   ├── ChatImagePicker.vue
│   │   │   └── ImagePreviewModal.vue
│   │   ├── layout/             # 佈局組件
│   │   │   └── NavBar.vue
│   │   └── ui/                 # UI 基礎組件
│   │       ├── AnimatedButton.vue
│   │       ├── Badge.vue
│   │       ├── FeatureCard.vue
│   │       ├── FloatingInput.vue
│   │       ├── GlassCard.vue
│   │       └── HeartLoader.vue
│   ├── views/                  # 頁面視圖
│   │   ├── Home.vue
│   │   ├── Register.vue
│   │   ├── Login.vue
│   │   ├── Profile.vue
│   │   ├── Discovery.vue
│   │   ├── Matches.vue
│   │   ├── ChatList.vue
│   │   ├── Chat.vue
│   │   ├── Blocked.vue
│   │   ├── ForgotPassword.vue
│   │   ├── MyReports.vue
│   │   ├── Notifications.vue
│   │   ├── ResetPassword.vue
│   │   ├── Settings.vue
│   │   ├── VerifyEmail.vue
│   │   └── admin/              # 管理後台
│   │       ├── AdminDashboard.vue
│   │       └── AdminLogin.vue
│   ├── stores/                 # Pinia stores
│   │   ├── user.js             # 用戶認證狀態
│   │   ├── profile.js          # 用戶檔案
│   │   ├── discovery.js        # 探索/配對
│   │   ├── chat.js             # 聊天
│   │   ├── safety.js           # 安全功能
│   │   ├── notification.js     # 通知
│   │   └── websocket.js        # WebSocket 狀態
│   ├── composables/            # Vue composables
│   │   └── useWebSocket.js
│   ├── router/                 # Vue Router
│   │   └── index.js
│   └── api/                    # API 客戶端
│       ├── client.js           # Axios 實例
│       └── auth.js             # 認證 API
└── vite.config.js
```

---

## 快速檢查清單

建立新組件時：

- [ ] 使用 `<script setup>` 語法
- [ ] 使用 `defineProps` 定義 props
- [ ] 使用 `defineEmits` 定義 emits
- [ ] 使用 `ref` 或 `reactive` 定義響應式狀態
- [ ] 使用 `computed` 定義衍生狀態
- [ ] API URL 無尾隨斜線
- [ ] 使用 try/catch 進行錯誤處理
- [ ] 為非同步操作加上載入狀態

---

## 核心模式

### 使用 Composition API 的組件

```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProfileStore } from '@/stores/profile'

// Props
const props = defineProps({
  userId: {
    type: String,
    required: true
  }
})

// Emits
const emit = defineEmits(['update', 'delete'])

// Store
const profileStore = useProfileStore()

// 響應式狀態
const loading = ref(false)
const error = ref(null)

// Computed
const hasPhotos = computed(() => {
  return profileStore.profile?.photos?.length > 0
})

// 方法
const handleUpdate = async () => {
  loading.value = true
  try {
    await profileStore.updateProfile(props.userId)
    emit('update')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// 生命週期
onMounted(async () => {
  await profileStore.fetchProfile(props.userId)
})
</script>

<template>
  <div class="profile-component">
    <div v-if="loading">載入中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- 內容 -->
    </div>
  </div>
</template>
```

### Pinia Store（Composition API 風格）

```javascript
// stores/profile.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api/client'

export const useProfileStore = defineStore('profile', () => {
  // State
  const profile = ref(null)
  const photos = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const hasProfile = computed(() => profile.value !== null)
  const primaryPhoto = computed(() => {
    return photos.value.find(photo => photo.is_primary)
  })

  // Actions
  const fetchProfile = async () => {
    loading.value = true
    try {
      // 無尾隨斜線
      const response = await apiClient.get('/profile')
      profile.value = response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateProfile = async (profileData) => {
    // 無尾隨斜線
    const response = await apiClient.patch('/profile', profileData)
    profile.value = response.data
    return response.data
  }

  return {
    // State
    profile,
    photos,
    loading,
    error,
    // Getters
    hasProfile,
    primaryPhoto,
    // Actions
    fetchProfile,
    updateProfile
  }
})
```

### 帶有認證守衛的 Vue Router

```javascript
// router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router
```

---

## 常見錯誤

### API URL 帶尾隨斜線（導致 404）

```javascript
// 錯誤
await axios.get('/api/profile/')     // 404
await axios.post('/api/photos/')     // 404

// 正確
await axios.get('/api/profile')
await axios.post('/api/photos', formData)
```

### 非響應式變數

```javascript
// 錯誤
let loading = false  // 不是響應式的

// 正確
const loading = ref(false)
```

### 直接修改 props

```vue
<script setup>
const props = defineProps(['value'])

// 錯誤 - props 是唯讀的
props.value = 'new'

// 正確 - 使用 emit
const emit = defineEmits(['update:value'])
emit('update:value', 'new')
</script>
```

### 缺少錯誤處理

```javascript
// 錯誤
async function fetchData() {
  const response = await axios.get('/api/profile')
  profile.value = response.data
}

// 正確
async function fetchData() {
  try {
    const response = await axios.get('/api/profile')
    profile.value = response.data
  } catch (error) {
    console.error('獲取失敗:', error)
    // 顯示用戶友善的錯誤訊息
  }
}
```

---

## 相關 Skills

- **api-routing-standards** - API URL 規則（必讀）
- **backend-dev-fastapi** - 後端 API 整合
