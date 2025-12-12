<!--
  NavBar.vue
  全域導航欄 - 頁面頂部 Header

  功能：
  - 顯示應用 Logo/標題
  - 整合 NotificationBell 通知鈴鐺組件
  - 提供導航連結
-->
<template>
  <header class="navbar" v-if="userStore.isAuthenticated">
    <div class="navbar-content">
      <!-- 左側：Logo/標題 -->
      <div class="navbar-left">
        <router-link to="/" class="logo-link">
          <span class="logo-text">MergeMeet</span>
        </router-link>
      </div>

      <!-- 中間：導航連結 -->
      <nav class="navbar-center">
        <router-link to="/discovery" class="nav-link" active-class="active">
          <n-icon size="20"><SearchOutline /></n-icon>
          <span class="nav-text">探索</span>
        </router-link>
        <router-link to="/matches" class="nav-link" active-class="active">
          <n-icon size="20"><Heart /></n-icon>
          <span class="nav-text">配對</span>
        </router-link>
        <router-link to="/messages" class="nav-link" active-class="active">
          <n-icon size="20"><ChatbubbleEllipses /></n-icon>
          <span class="nav-text">訊息</span>
        </router-link>
      </nav>

      <!-- 右側：通知鈴鐺 + 用戶選單 -->
      <div class="navbar-right">
        <!-- 通知鈴鐺 -->
        <NotificationBell />

        <!-- 用戶選單 -->
        <n-dropdown :options="userMenuOptions" @select="handleUserMenuSelect">
          <n-button text class="user-menu-btn">
            <n-avatar
              v-if="userAvatar"
              :src="userAvatar"
              :size="32"
              round
            />
            <n-avatar
              v-else
              :size="32"
              round
            >
              {{ userInitial }}
            </n-avatar>
          </n-button>
        </n-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NDropdown, NButton, NAvatar } from 'naive-ui'
import {
  SearchOutline,
  Heart,
  ChatbubbleEllipses,
  PersonOutline,
  SettingsOutline,
  LogOutOutline
} from '@vicons/ionicons5'
import { useUserStore } from '@/stores/user'
import { useProfileStore } from '@/stores/profile'
import NotificationBell from '@/components/NotificationBell.vue'

const router = useRouter()
const userStore = useUserStore()
const profileStore = useProfileStore()

/**
 * 用戶頭像
 */
const userAvatar = computed(() => {
  const profile = profileStore.profile
  if (profile?.photos?.length > 0) {
    const primaryPhoto = profile.photos.find(p => p.is_primary)
    return primaryPhoto?.url || profile.photos[0]?.url
  }
  return null
})

/**
 * 用戶名稱首字母（無頭像時顯示）
 */
const userInitial = computed(() => {
  const name = profileStore.profile?.display_name || userStore.user?.email || ''
  return name.charAt(0).toUpperCase()
})

/**
 * 渲染圖示
 */
const renderIcon = (icon) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

/**
 * 用戶選單選項
 */
const userMenuOptions = [
  {
    label: '個人檔案',
    key: 'profile',
    icon: renderIcon(PersonOutline)
  },
  {
    label: '設定',
    key: 'settings',
    icon: renderIcon(SettingsOutline)
  },
  {
    type: 'divider',
    key: 'd1'
  },
  {
    label: '登出',
    key: 'logout',
    icon: renderIcon(LogOutOutline)
  }
]

/**
 * 處理用戶選單選擇
 */
const handleUserMenuSelect = (key) => {
  switch (key) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/profile')  // 暫時導向 profile，未來可新增設定頁
      break
    case 'logout':
      userStore.logout()
      router.push('/login')
      break
  }
}
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background-color: #fff;
  border-bottom: 1px solid #f0f0f0;
  z-index: 1000;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.navbar-content {
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
}

/* 左側 */
.navbar-left {
  flex: 0 0 auto;
}

.logo-link {
  text-decoration: none;
}

.logo-text {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #ff6b6b 0%, #ff8e8e 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 中間導航 */
.navbar-center {
  display: flex;
  gap: 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  text-decoration: none;
  color: #666;
  transition: all 0.2s;
  font-size: 14px;
}

.nav-link:hover {
  background-color: #f5f5f5;
  color: #333;
}

.nav-link.active {
  background-color: #fff0f0;
  color: #ff6b6b;
}

.nav-text {
  font-weight: 500;
}

/* 右側 */
.navbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-menu-btn {
  padding: 4px;
  border-radius: 50%;
}

.user-menu-btn:hover {
  background-color: #f5f5f5;
}

/* 響應式 */
@media (max-width: 768px) {
  .nav-text {
    display: none;
  }

  .nav-link {
    padding: 8px 12px;
  }

  .logo-text {
    font-size: 18px;
  }
}
</style>
