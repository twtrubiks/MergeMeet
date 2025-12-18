---
name: frontend-dev-vue3
description: This skill should be used when developing frontend features for MergeMeet. It provides guidance on Vue 3 Composition API + Pinia + Vue Router patterns including component design, state management, routing, API integration, and WebSocket handling.
---

# Vue 3 Frontend Development Guide

## Purpose

To establish consistent patterns for Vue 3 + Pinia + Vue Router development in the MergeMeet project.

---

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable Vue components
│   │   ├── InterestSelector.vue
│   │   ├── MatchModal.vue
│   │   ├── PhotoUploader.vue
│   │   ├── ReportModal.vue
│   │   └── chat/
│   │       └── MessageBubble.vue
│   ├── views/            # Page views
│   │   ├── Home.vue
│   │   ├── Register.vue
│   │   ├── Login.vue
│   │   ├── Profile.vue
│   │   ├── Discovery.vue
│   │   ├── Matches.vue
│   │   ├── ChatList.vue
│   │   ├── Chat.vue
│   │   └── admin/
│   ├── stores/           # Pinia stores
│   │   ├── auth.js
│   │   ├── profile.js
│   │   ├── discovery.js
│   │   ├── match.js
│   │   ├── chat.js
│   │   └── safety.js
│   ├── composables/      # Vue composables
│   │   └── useWebSocket.js
│   ├── router/           # Vue Router
│   │   └── index.js
│   └── api/              # API client
│       └── axios.js
└── vite.config.js
```

---

## Quick Checklist

When creating new components:

- [ ] Use `<script setup>` syntax
- [ ] Define props with `defineProps`
- [ ] Define emits with `defineEmits`
- [ ] Use `ref` or `reactive` for reactive state
- [ ] Use `computed` for derived state
- [ ] API URLs have no trailing slash
- [ ] Add error handling with try/catch
- [ ] Add loading state for async operations

---

## Core Patterns

### Component with Composition API

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

// Reactive state
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
    <div v-if="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Content -->
    </div>
  </div>
</template>
```

### Pinia Store

```javascript
// stores/profile.js
import { defineStore } from 'pinia'
import axios from 'axios'

export const useProfileStore = defineStore('profile', {
  state: () => ({
    profile: null,
    photos: [],
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
        // No trailing slash
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
      // No trailing slash
      const response = await axios.put('/api/profile', profileData)
      this.profile = response.data
      return response.data
    }
  }
})
```

### Vue Router with Auth Guard

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
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

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

---

## Common Mistakes

### API URL with trailing slash (causes 404)

```javascript
// Wrong
await axios.get('/api/profile/')     // 404
await axios.post('/api/photos/')     // 404

// Correct
await axios.get('/api/profile')
await axios.post('/api/photos', formData)
```

### Non-reactive variable

```javascript
// Wrong
let loading = false  // Not reactive

// Correct
const loading = ref(false)
```

### Modifying props directly

```vue
<script setup>
const props = defineProps(['value'])

// Wrong - props are readonly
props.value = 'new'

// Correct - use emit
const emit = defineEmits(['update:value'])
emit('update:value', 'new')
</script>
```

### Missing error handling

```javascript
// Wrong
async function fetchData() {
  const response = await axios.get('/api/profile')
  profile.value = response.data
}

// Correct
async function fetchData() {
  try {
    const response = await axios.get('/api/profile')
    profile.value = response.data
  } catch (error) {
    console.error('Failed to fetch:', error)
    // Show user-friendly error message
  }
}
```

---

## Related Skills

- **api-routing-standards** - API URL rules (required reading)
- **backend-dev-fastapi** - Backend API integration
