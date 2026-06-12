import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '../api'
import { ElMessage } from 'element-plus'
import router from '../router'
import { usePointsStore } from './points'

export const useUserStore = defineStore('user', () => {
  const username = ref('')
  const token = ref(localStorage.getItem('token') || '')
  const isMember = ref(false)
  const memberExpireAt = ref(null)
  const subscriptionPlan = ref(null)
  const subscriptionPeriod = ref(null)
  const subscriptionExpireAt = ref(null)
  const loading = ref(false)
  const lastError = ref('')
  let userInfoRequest = null

  const isLoggedIn = computed(() => !!token.value)

  async function login(loginUsername, password) {
    const res = await api.post('/auth/login', {
      username: loginUsername,
      password: password
    })
    token.value = res.data.access_token
    localStorage.setItem('token', res.data.access_token)
    username.value = loginUsername
    await refreshUserInfoQuietly()
  }

  async function register(registerUsername, password) {
    await api.post('/auth/register', {
      username: registerUsername,
      password: password
    })
    ElMessage.success('注册成功，请登录')
  }

  function logout() {
    token.value = ''
    username.value = ''
    isMember.value = false
    memberExpireAt.value = null
    subscriptionPlan.value = null
    subscriptionPeriod.value = null
    subscriptionExpireAt.value = null
    localStorage.removeItem('token')
    router.push('/login')
  }

  async function fetchUserInfo() {
    if (userInfoRequest) return userInfoRequest
    loading.value = true
    lastError.value = ''
    userInfoRequest = api.get('/points/balance')
      .then((res) => {
        const data = res.data
        username.value = data.username || username.value
        isMember.value = data.is_member || false
        memberExpireAt.value = data.member_expire_at || null
        subscriptionPlan.value = data.subscription_plan || null
        subscriptionPeriod.value = data.subscription_period || null
        subscriptionExpireAt.value = data.subscription_expire_at || data.member_expire_at || null

        const pointsStore = usePointsStore()
        pointsStore.applyBalance(data)
        return data
      })
      .catch((e) => {
        lastError.value = e.response?.data?.detail || '用户信息刷新失败'
        throw e
      })
      .finally(() => {
        loading.value = false
        userInfoRequest = null
      })
    return userInfoRequest
  }

  async function refreshUserInfoQuietly() {
    try {
      await fetchUserInfo()
    } catch (_) {}
  }

  return {
    username,
    token,
    isMember,
    memberExpireAt,
    subscriptionPlan,
    subscriptionPeriod,
    subscriptionExpireAt,
    loading,
    lastError,
    isLoggedIn,
    login,
    register,
    logout,
    fetchUserInfo,
    refreshUserInfoQuietly
  }
})
