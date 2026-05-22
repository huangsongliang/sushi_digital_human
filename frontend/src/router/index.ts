import { createRouter, createWebHistory } from 'vue-router'
import ChatPage from '../components/ChatPage.vue'
import AuthPage from '../components/AuthPage.vue'
import DocumentManager from '../components/DocumentManager.vue'
import GithubCallback from '../components/GithubCallback.vue'
import DemoPage from '../components/DemoPage.vue'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    name: 'Chat',
    component: ChatPage,
    meta: { requiresAuth: true },
  },
  {
    path: '/documents',
    name: 'Documents',
    component: DocumentManager,
    meta: { requiresAuth: true },
  },
  {
    path: '/demo',
    name: 'Demo',
    component: DemoPage,
  },
  {
    path: '/login',
    name: 'Login',
    component: AuthPage,
  },
  {
    path: '/register',
    name: 'Register',
    component: AuthPage,
  },
  {
    path: '/github/callback',
    name: 'GithubCallback',
    component: GithubCallback,
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: AuthPage,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && authStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

// 监听 Token 过期事件（来自 request.ts 的 401 自动刷新失败）
window.addEventListener('auth:logout', () => {
  const authStore = useAuthStore()
  authStore.logout()
  router.push('/login')
})

export default router
