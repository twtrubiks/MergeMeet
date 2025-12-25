<template>
  <n-config-provider>
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <div id="app">
            <!-- 全域導航欄（已登入時顯示） -->
            <NavBar />

            <!-- 主要內容區域 -->
            <main :class="{ 'with-navbar': userStore.isAuthenticated }">
              <RouterView />
            </main>
          </div>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { RouterView } from 'vue-router'
import { NConfigProvider, NMessageProvider, NDialogProvider, NNotificationProvider } from 'naive-ui'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { useNotificationStore } from '@/stores/notification'
import { useChatStore } from '@/stores/chat'
import { useProfileStore } from '@/stores/profile'
import NavBar from '@/components/layout/NavBar.vue'

const userStore = useUserStore()
const wsStore = useWebSocketStore()
const notificationStore = useNotificationStore()
const chatStore = useChatStore()
const profileStore = useProfileStore()

// 初始化：從 token 恢復用戶資料
onMounted(() => {
  userStore.initializeFromToken()

  // 初始化通知監聽器（註冊三種通知類型的處理器）
  notificationStore.initNotificationListeners()

  // 初始化聊天訊息處理器
  chatStore.initChatHandlers()

  // 啟動全域 WebSocket 自動連接監聽
  wsStore.initAutoConnect()
})

// 統一處理登入/登出狀態變化（包含頁面刷新時的初始載入）
watch(
  () => userStore.isAuthenticated,
  async (isAuth) => {
    if (isAuth) {
      // 用戶登入時，並行載入 profile 和通知
      await Promise.all([
        profileStore.fetchProfile().catch(() => {
          // Profile 不存在是正常情況（新用戶）
        }),
        notificationStore.fetchNotifications().catch(err => {
          console.error('Failed to fetch notifications:', err)
        })
      ])
    } else {
      // 用戶登出時，重置狀態
      profileStore.$reset()
      notificationStore.$reset()
      chatStore.$reset()
    }
  },
  { immediate: true }  // 頁面載入時立即執行，處理刷新情況
)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background-color: #f5f5f5;
}

#app {
  min-height: 100vh;
}

/* 有導航欄時，主要內容區域需要留出頂部空間 */
main.with-navbar {
  padding-top: 56px;  /* NavBar 高度 */
}

/* 尊重用戶的減少動畫偏好設置 (可訪問性) */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>
