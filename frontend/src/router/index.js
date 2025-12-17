import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import Home from '@/views/Home.vue'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import ForgotPassword from '@/views/ForgotPassword.vue'
import ResetPassword from '@/views/ResetPassword.vue'
import VerifyEmail from '@/views/VerifyEmail.vue'
import Profile from '@/views/Profile.vue'
import Discovery from '@/views/Discovery.vue'
import Matches from '@/views/Matches.vue'
import Blocked from '@/views/Blocked.vue'
import ChatList from '@/views/ChatList.vue'
import Chat from '@/views/Chat.vue'
import AdminLogin from '@/views/admin/AdminLogin.vue'
import AdminDashboard from '@/views/admin/AdminDashboard.vue'

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
      component: Register,
      meta: { requiresAuth: false }
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: ForgotPassword,
      meta: { requiresAuth: false }
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: ResetPassword,
      meta: { requiresAuth: false }
    },
    {
      path: '/verify-email',
      name: 'verify-email',
      component: VerifyEmail,
      meta: { requiresAuth: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: Profile,
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/discovery',
      name: 'discovery',
      component: Discovery,
      meta: { requiresAuth: true }
    },
    {
      path: '/matches',
      name: 'matches',
      component: Matches,
      meta: { requiresAuth: true }
    },
    {
      path: '/blocked',
      name: 'blocked',
      component: Blocked,
      meta: { requiresAuth: true }
    },
    {
      path: '/messages',
      name: 'messages',
      component: ChatList,
      meta: { requiresAuth: true }
    },
    {
      path: '/messages/:matchId',
      name: 'chat',
      component: Chat,
      meta: { requiresAuth: true }
    },
    {
      path: '/admin/login',
      name: 'admin-login',
      component: AdminLogin,
      meta: { requiresAuth: false, requiresAdmin: false }
    },
    {
      path: '/admin',
      name: 'admin-dashboard',
      component: AdminDashboard,
      meta: { requiresAuth: true, requiresAdmin: true }
    }
  ]
})

// 路由守衛：檢查認證狀態和管理員權限
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  // 檢查是否需要認證
  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    // 需要認證但未登入，導向登入頁
    next('/login')
    return
  }

  // 檢查是否需要 Email 驗證（已登入但未驗證）
  if (to.meta.requiresAuth &&
      userStore.isAuthenticated &&
      !userStore.user?.email_verified &&
      to.path !== '/verify-email') {
    // 已登入但未驗證 Email，導向驗證頁面
    next('/verify-email')
    return
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
