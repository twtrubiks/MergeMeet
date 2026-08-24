<!--
  NavBar.vue
  全域導航欄 - 頁面頂部 Header

  功能：
  - 顯示應用 Logo/標題
  - 整合 NotificationBell 通知鈴鐺組件
  - 提供導航連結
-->
<template>
  <header v-if="userStore.isAuthenticated" class="navbar">
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
          <Icon name="search" size="sm" decorative />
          <span class="nav-text">探索</span>
        </router-link>
        <router-link to="/matches" class="nav-link" active-class="active">
          <Icon name="heart" size="sm" decorative />
          <span class="nav-text">配對</span>
        </router-link>
        <router-link to="/messages" class="nav-link" active-class="active">
          <Icon name="chat" size="sm" decorative />
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
            <n-avatar v-if="userAvatar" :src="userAvatar" :size="32" round object-fit="cover" />
            <n-avatar v-else :size="32" round>
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
import { PersonOutline, SettingsOutline, LogOutOutline, ShieldOutline } from '@vicons/ionicons5'
import { useUserStore } from '@/stores/user'
import { useProfileStore } from '@/stores/profile'
import NotificationBell from '@/components/NotificationBell.vue'
import Icon from '@/components/ui/Icon.vue'

const router = useRouter()
const userStore = useUserStore()
const profileStore = useProfileStore()

/**
 * 用戶頭像（優先用正方形縮圖節省流量，無縮圖時退回原圖）
 */
const userAvatar = computed(() => {
  const profile = profileStore.profile
  if (profile?.photos?.length > 0) {
    const primaryPhoto = profile.photos.find((p) => p.is_profile_picture) || profile.photos[0]
    return primaryPhoto?.thumbnail_url || primaryPhoto?.url || null
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
 * 用戶選單選項（根據用戶角色動態生成）
 */
const userMenuOptions = computed(() => {
  const options = [
    {
      label: '個人檔案',
      key: 'profile',
      icon: renderIcon(PersonOutline)
    },
    {
      label: '設定',
      key: 'settings',
      icon: renderIcon(SettingsOutline)
    }
  ]

  // 管理員用戶顯示管理後台入口
  if (userStore.isAdmin) {
    options.push({
      type: 'divider',
      key: 'd1'
    })
    options.push({
      label: '管理後台',
      key: 'admin',
      icon: renderIcon(ShieldOutline)
    })
  }

  options.push({
    type: 'divider',
    key: 'd2'
  })
  options.push({
    label: '登出',
    key: 'logout',
    icon: renderIcon(LogOutOutline)
  })

  return options
})

/**
 * 處理用戶選單選擇
 */
const handleUserMenuSelect = (key) => {
  switch (key) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'admin':
      router.push('/admin')
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
  background-color: var(--color-surface);
  border-bottom: 1px solid var(--color-border-light);
  z-index: var(--z-modal);
  box-shadow: var(--shadow-sm);
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
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  background: var(--color-primary-gradient);
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
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--color-text-muted);
  transition: all var(--duration-normal);
  font-size: var(--font-size-sm);
  min-height: var(--touch-target-min);
}

.nav-link:hover {
  background-color: var(--color-background-light);
  color: var(--color-text-primary);
}

.nav-link:focus-visible {
  outline: 3px solid var(--color-primary-600);
  outline-offset: -3px;
}

.nav-link.active {
  background-color: var(--color-primary-alpha-10);
  color: var(--color-primary-600);
}

.nav-text {
  font-weight: var(--font-weight-medium);
}

/* 右側 */
.navbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-menu-btn {
  padding: var(--space-1);
  border-radius: var(--radius-full);
  min-width: var(--touch-target-min);
  min-height: var(--touch-target-min);
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-menu-btn:hover {
  background-color: var(--color-background-light);
}

/* 響應式 */
@media (max-width: 768px) {
  .nav-text {
    display: none;
  }

  .nav-link {
    padding: var(--space-2) var(--space-3);
    min-width: var(--touch-target-min);
    min-height: var(--touch-target-min);
  }

  .logo-text {
    font-size: var(--font-size-lg);
  }
}

/* 極小螢幕 */
@media (max-width: 360px) {
  .navbar-content {
    padding: 0 var(--space-2);
  }

  .navbar-center {
    gap: var(--space-1);
  }

  .nav-link {
    padding: var(--space-2);
  }
}
</style>
