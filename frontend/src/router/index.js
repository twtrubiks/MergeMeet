import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import Home from '@/views/Home.vue'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import Profile from '@/views/Profile.vue'
import Discovery from '@/views/Discovery.vue'
import Matches from '@/views/Matches.vue'
import Blocked from '@/views/Blocked.vue'
import ChatList from '@/views/ChatList.vue'
import Chat from '@/views/Chat.vue'

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
      path: '/profile',
      name: 'profile',
      component: Profile,
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
    }
  ]
})

// 路由守衛：檢查認證狀態
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    // 需要認證但未登入，導向登入頁
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && userStore.isAuthenticated) {
    // 已登入但訪問登入/註冊頁，導向首頁
    next('/')
  } else {
    next()
  }
})

export default router
