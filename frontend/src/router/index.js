import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useProfileStore } from '@/stores/profile'
import { refreshAuthToken } from '@/api/client'
import { discreteMessage } from '@/utils/discreteApi'
import Home from '@/views/Home.vue'
import Login from '@/views/Login.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: { requiresAuth: false }
    },
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('@/views/ForgotPassword.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('@/views/ResetPassword.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/verify-email',
      name: 'verify-email',
      component: () => import('@/views/VerifyEmail.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/Profile.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('@/views/Notifications.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/my-reports',
      name: 'my-reports',
      component: () => import('@/views/MyReports.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/discovery',
      name: 'discovery',
      component: () => import('@/views/Discovery.vue'),
      meta: { requiresAuth: true, requiresCompleteProfile: true }
    },
    {
      path: '/likes-you',
      name: 'likes-you',
      component: () => import('@/views/LikesYou.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/matches',
      name: 'matches',
      component: () => import('@/views/Matches.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/blocked',
      name: 'blocked',
      component: () => import('@/views/Blocked.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/messages',
      name: 'messages',
      component: () => import('@/views/ChatList.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/messages/:matchId',
      name: 'chat',
      component: () => import('@/views/Chat.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('@/views/admin/AdminLogin.vue'),
      meta: { requiresAuth: false, requiresAdmin: false }
    },
    {
      path: '/admin',
      name: 'admin-dashboard',
      component: () => import('@/views/admin/AdminDashboard.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    }
  ]
})

// 路由守衛：檢查認證狀態、Profile 完整性和管理員權限
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  // 曾登入過（localStorage 留有 access token）但已過期 → 先以 refresh cookie 靜默續期。
  // 不限 requiresAuth 路由：首頁等公開頁重整時也要恢復登入狀態，否則會看起來像被登出
  if (!userStore.isAuthenticated && localStorage.getItem('access_token')) {
    try {
      // 成功時 'token-refreshed' 事件會同步更新 Pinia Store
      await refreshAuthToken()
    } catch (error) {
      // 只有後端明確拒絕（401：refresh cookie 過期、失效或未帶上）才清除殘留 token。
      // 網路錯誤或 5xx（例如電腦喚醒瞬間、後端重啟中）保留 token，下次導航再試，
      // 否則一次瞬斷就會永久登出，即使 refresh cookie 還有效
      if (error.response?.status === 401) {
        userStore.clearTokens()
      }
    }
  }

  // 檢查是否需要認證
  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    // 需要認證但未登入，導向登入頁
    next('/login')
    return
  }

  // 檢查是否需要 Email 驗證（已登入但未驗證）
  if (
    to.meta.requiresAuth &&
    userStore.isAuthenticated &&
    !userStore.user?.email_verified &&
    to.path !== '/verify-email'
  ) {
    // 已登入但未驗證 Email，導向驗證頁面
    next('/verify-email')
    return
  }

  // 檢查是否需要完整 Profile
  if (to.meta.requiresCompleteProfile && userStore.isAuthenticated) {
    const profileStore = useProfileStore()

    // 確保 Profile 數據已載入
    if (!profileStore.hasProfile) {
      try {
        await profileStore.fetchProfile()
      } catch (error) {
        console.warn('Failed to fetch profile for route guard:', error)
      }
    }

    // 檢查 Profile 是否完整
    if (!profileStore.isProfileComplete) {
      discreteMessage.warning('請先完成個人檔案設定（需要至少一張照片）', {
        duration: 4000,
        closable: true
      })
      next('/profile')
      return
    }
  }

  // 檢查是否需要管理員權限
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    // 需要管理員權限但不是管理員，導向管理員登入頁
    next('/admin/login')
    return
  }

  // 已登入但訪問登入/註冊頁，導向首頁
  if ((to.path === '/login' || to.path === '/register') && userStore.isAuthenticated) {
    next('/')
    return
  }

  // 已是管理員但訪問管理員登入頁，導向管理後台
  if (to.path === '/admin/login' && userStore.isAdmin) {
    next('/admin')
    return
  }

  next()
})

export default router
