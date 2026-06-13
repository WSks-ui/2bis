import { createRouter, createWebHistory } from 'vue-router'
import api from '../api'

const loadLoginView = () => import('../views/Login.vue')
const loadRegisterView = () => import('../views/Register.vue')
const loadHomeView = () => import('../views/Home.vue')
const loadRechargeView = () => import('../views/Recharge.vue')
const loadHistoryView = () => import('../views/History.vue')
const loadAdminApiKeysView = () => import('../views/AdminApiKeys.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: loadLoginView
  },
  {
    path: '/register',
    name: 'Register',
    component: loadRegisterView
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
  const token = localStorage.getItem('token')
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

export function preloadPlansRoute() {
  return loadRechargeView().catch(() => {})
}

export function preloadAdminApiKeysRoute() {
  return loadAdminApiKeysView().catch(() => {})
}
