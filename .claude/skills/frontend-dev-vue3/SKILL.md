---
name: frontend-dev-vue3
description: Vue 3 Composition API + Pinia + Vue Router 開發指南。涵蓋組件設計、狀態管理、路由配置、API 整合、WebSocket、表單驗證、載入狀態等。適用於 MergeMeet 交友平台前端開發。
---

# Vue 3 前端開發指南

## 🎯 目的

建立 Vue 3 + Pinia + Vue Router 開發的一致性與最佳實踐。

---

## 📚 何時使用此 Skill

**自動觸發**:
- 編輯 `frontend/src/**/*.vue` 或 `**/*.js` 檔案
- 關鍵字: "component", "vue", "pinia", "前端", "組件", "頁面"
- 程式碼包含: `<script setup>`, `defineProps`, `usePinia`, `createRouter`

**手動使用**:
```bash
使用 Skill: frontend-dev-vue3
```

---

## 🏗️ 專案架構

```
frontend/
├── src/
│   ├── components/       # Vue 組件（5 個）
│   │   ├── InterestSelector.vue
│   │   ├── MatchModal.vue
│   │   ├── PhotoUploader.vue
│   │   ├── ReportModal.vue
│   │   └── chat/
│   │       └── MessageBubble.vue
│   ├── views/            # 頁面視圖（11 個）
│   │   ├── Home.vue
│   │   ├── Register.vue
│   │   ├── Login.vue
│   │   ├── Profile.vue
│   │   ├── Discovery.vue
│   │   ├── Matches.vue
│   │   ├── ChatList.vue
│   │   ├── Chat.vue
│   │   ├── Blocked.vue
│   │   └── admin/
│   │       ├── AdminLogin.vue
│   │       └── AdminDashboard.vue
│   ├── stores/           # Pinia Stores（7 個）
│   │   ├── auth.js
│   │   ├── profile.js
│   │   ├── discovery.js
│   │   ├── match.js
│   │   ├── chat.js
│   │   ├── safety.js
│   │   └── user.js
│   ├── composables/      # Vue Composables
│   │   └── useWebSocket.js
│   ├── router/           # Vue Router
│   │   └── index.js
│   └── api/              # API 客戶端
│       └── axios.js
├── package.json
└── vite.config.js
```

---

## ⚡ 快速檢查清單

創建新組件時：

- [ ] **Composition API** - 使用 `<script setup>`
- [ ] **Props 定義** - 使用 `defineProps` with TypeScript
- [ ] **響應式變數** - `ref` 或 `reactive`
- [ ] **計算屬性** - `computed` for derived state
- [ ] **方法** - 正常函數或箭頭函數
- [ ] **生命週期** - `onMounted`, `onUnmounted` etc.
- [ ] **Pinia Store** - `useXxxStore()` 獲取狀態
- [ ] **API 請求** - 無尾隨斜線 ⚠️
- [ ] **錯誤處理** - try/catch + 用戶提示
- [ ] **載入狀態** - loading flag

---

## 📖 資源檔案導覽

| 需要... | 閱讀此檔案 |
|--------|----------|
| 組件設計模式 | [component-patterns.md](resources/component-patterns.md) |
| Pinia 狀態管理 | [state-management.md](resources/state-management.md) |
| Vue Router 配置 | [routing-guide.md](resources/routing-guide.md) |
| API 整合 | [api-integration.md](resources/api-integration.md) |
| WebSocket 使用 | [websocket-patterns.md](resources/websocket-patterns.md) |
| 表單處理 | [form-validation.md](resources/form-validation.md) |
| 載入與錯誤 | [loading-states.md](resources/loading-states.md) |
| 檔案組織 | [file-organization.md](resources/file-organization.md) |
| 完整範例 | [complete-examples.md](resources/complete-examples.md) |

---

## 🔍 查詢官方文檔 (Context7 MCP)

```bash
# Vue 3 文檔
context7: resolve-library-id "vue"
context7: get-library-docs "/vuejs/core" topic="composition api"
context7: get-library-docs "/vuejs/core" topic="reactivity"

# Pinia 文檔
context7: resolve-library-id "pinia"
context7: get-library-docs "/vuejs/pinia" topic="state management"

# Vue Router 文檔
context7: resolve-library-id "vue-router"
context7: get-library-docs "/vuejs/router" topic="navigation"

# Axios 文檔
context7: resolve-library-id "axios"
context7: get-library-docs "/axios/axios" topic="requests"
```

---

## 🧪 測試前端功能 (Chrome DevTools MCP)

使用 **chrome-devtools MCP** 進行前端測試：

```bash
# 在瀏覽器中測試
1. 打開應用: http://localhost:5173
2. 使用 Chrome DevTools MCP 查看 Console
3. 檢查 Network 請求
4. 查看 Vue DevTools
```

**常見檢查**:
- Console 是否有錯誤？
- Network 請求的 URL 是否正確（無尾隨斜線）？
- API 回應狀態碼是什麼（200/404/500）？
- Vue DevTools 中的 Pinia state 是否正確更新？

---

## 🚀 核心模式

### 1. Composition API 組件模式
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

// Emit
const emit = defineEmits(['update', 'delete'])

// Store
const profileStore = useProfileStore()

// Reactive State
const loading = ref(false)
const error = ref(null)

// Computed
const hasPhotos = computed(() => {
  return profileStore.profile?.photos?.length > 0
})

// Methods
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

// Lifecycle
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

<style scoped>
.profile-component {
  padding: 20px;
}
</style>
```

### 2. Pinia Store 模式
```javascript
// stores/profile.js
import { defineStore } from 'pinia'
import axios from 'axios'

export const useProfileStore = defineStore('profile', {
  state: () => ({
    profile: null,
    photos: [],
    interests: [],
    loading: false,
    error: null
  }),

  getters: {
    hasProfile: (state) => state.profile !== null,
    primaryPhoto: (state) => {
      return state.photos.find(photo => photo.is_primary)
    }
  },

  actions: {
    async fetchProfile() {
      this.loading = true
      try {
        // ⚠️ 重要：無尾隨斜線
        const response = await axios.get('/api/profile')
        this.profile = response.data
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateProfile(profileData) {
      try {
        // ⚠️ 重要：無尾隨斜線
        const response = await axios.put('/api/profile', profileData)
        this.profile = response.data
        return response.data
      } catch (error) {
        throw error
      }
    },

    async uploadPhoto(file) {
      const formData = new FormData()
      formData.append('file', file)

      try {
        // ⚠️ 重要：無尾隨斜線
        const response = await axios.post('/api/profile/photos', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        await this.fetchProfile()  // 重新獲取
        return response.data
      } catch (error) {
        throw error
      }
    }
  }
})
```

### 3. Vue Router 模式
```javascript
// router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
    meta: { requiresAuth: true }  // 需要認證
  },
  {
    path: '/discovery',
    name: 'Discovery',
    component: () => import('@/views/Discovery.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 導航守衛
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router
```

### 4. Axios 配置模式
```javascript
// api/axios.js
import axios from 'axios'
import router from '@/router'

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request 攔截器
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response 攔截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token 過期，導向登入
      localStorage.removeItem('token')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

### 5. WebSocket Composable 模式
```javascript
// composables/useWebSocket.js
import { ref, onUnmounted } from 'vue'

export function useWebSocket(url) {
  const ws = ref(null)
  const messages = ref([])
  const isConnected = ref(false)

  const connect = (token) => {
    ws.value = new WebSocket(`${url}?token=${token}`)

    ws.value.onopen = () => {
      isConnected.value = true
      console.log('WebSocket connected')
    }

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      messages.value.push(data)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.value.onclose = () => {
      isConnected.value = false
      console.log('WebSocket disconnected')
      // 自動重連
      setTimeout(() => connect(token), 3000)
    }
  }

  const send = (message) => {
    if (ws.value && isConnected.value) {
      ws.value.send(JSON.stringify(message))
    }
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.close()
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    messages,
    isConnected,
    connect,
    send,
    disconnect
  }
}
```

---

## ⚠️ 常見錯誤

### 錯誤 1: API URL 有尾隨斜線
```javascript
// ❌ 錯誤 - 會導致 404
await axios.get('/api/profile/')
await axios.post('/api/profile/photos/', formData)

// ✅ 正確
await axios.get('/api/profile')
await axios.post('/api/profile/photos', formData)
```

### 錯誤 2: 忘記響應式
```javascript
// ❌ 錯誤
let loading = false  // 不是響應式

// ✅ 正確
const loading = ref(false)
```

### 錯誤 3: 直接修改 props
```vue
<script setup>
const props = defineProps(['value'])

// ❌ 錯誤
props.value = 'new'  // Props 是唯讀的！

// ✅ 正確 - 使用 emit
const emit = defineEmits(['update:value'])
emit('update:value', 'new')
</script>
```

### 錯誤 4: 忘記處理錯誤
```javascript
// ❌ 錯誤
async function fetchData() {
  const response = await axios.get('/api/profile')
  profile.value = response.data
}

// ✅ 正確
async function fetchData() {
  try {
    const response = await axios.get('/api/profile')
    profile.value = response.data
  } catch (error) {
    console.error('獲取資料失敗:', error)
    // 顯示錯誤訊息給用戶
  }
}
```

---

## 🔗 相關 Skills

- **api-routing-standards** - API URL 規範（必讀）
- **backend-dev-fastapi** - 後端 API 對應
- **testing-guide** - 前端測試策略

---

## 📝 核心原則

1. **Composition API** - 使用 `<script setup>` 語法
2. **響應式優先** - `ref` 和 `reactive`
3. **Pinia 狀態管理** - 全域狀態統一管理
4. **無尾隨斜線** - 所有 API URL 不使用 `/` 結尾 ⚠️
5. **錯誤處理** - try/catch + 用戶友好提示
6. **載入狀態** - 提供視覺回饋
7. **路由守衛** - 保護需要認證的頁面

---

**Skill 狀態**: ✅ COMPLETE
**優先級**: HIGH
**行數**: < 450 行 ✅
