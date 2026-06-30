import { createRouter, createWebHistory } from 'vue-router'
import api from '../api'
import { getStoredToken } from '../services/authToken'

const loadAuthView = () => import('../views/AuthView.vue')
const loadHomeView = () => import('../views/Home.vue')
const loadRechargeView = () => import('../views/Recharge.vue')
const loadHistoryView = () => import('../views/History.vue')
const loadAdminApiKeysView = () => import('../views/AdminApiKeys.vue')
const loadStudioView = () => import('../views/Studio.vue')
const loadStudioWorkspaceView = () => import('../views/StudioWorkspace.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: loadAuthView
  },
  {
    path: '/register',
    name: 'Register',
    component: loadAuthView
  },
  {
    path: '/',
    name: 'Home',
    component: loadHomeView,
    meta: { requiresAuth: true }
  },
  {
    path: '/plans',
    name: 'Plans',
    component: loadRechargeView,
    meta: { requiresAuth: true }
  },
  {
    path: '/recharge',
    redirect: '/plans'
  },
  {
    path: '/history',
    name: 'History',
    component: loadHistoryView,
    meta: { requiresAuth: true }
  },
  {
    path: '/studio',
    name: 'Studio',
    component: loadStudioView,
    meta: { requiresAuth: true }
  },
  {
    path: '/studio/:workspaceId',
    name: 'StudioWorkspace',
    component: loadStudioWorkspaceView,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/api-keys',
    name: 'AdminApiKeys',
    component: loadAdminApiKeysView,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = getStoredToken()
  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }
  if (to.meta.requiresAdmin) {
    api.get('/points/balance')
      .then((res) => {
        if (!res.data?.is_admin) {
          next('/')
          return
        }
        next()
      })
      .catch(() => {
        next('/')
      })
    return
  }
  next()
})

export default router

export function preloadHistoryRoute() {
  return loadHistoryView().catch(() => {})
}

export function preloadStudioRoute() {
  return Promise.allSettled([
    loadStudioView(),
    loadStudioWorkspaceView(),
  ])
}

export function preloadPlansRoute() {
  return loadRechargeView().catch(() => {})
}

export function preloadAdminApiKeysRoute() {
  return loadAdminApiKeysView().catch(() => {})
}

export function preloadAuthRoutes() {
  // 登录/注册页共享同一个壳层，提前拉取 chunk 可避免首次切换时出现白屏等待。
  return loadAuthView().catch(() => {})
}
