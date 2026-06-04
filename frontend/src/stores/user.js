import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'
import { ElMessage } from 'element-plus'
import router from '../router'
import { usePointsStore } from './points'

export const useUserStore = defineStore('user', () => {
  const username = ref('')
  const token = ref(localStorage.getItem('token') || '')
  const isMember = ref(false)
  const memberExpireAt = ref(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(loginUsername, password) {
    const res = await api.post('/auth/login', {
      username: loginUsername,
      password: password
    })
    token.value = res.data.access_token
    localStorage.setItem('token', res.data.access_token)
    username.value = loginUsername
    await fetchUserInfo()
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
    localStorage.removeItem('token')
    router.push('/login')
  }

  async function fetchUserInfo() {
    try {
      const res = await api.get('/points/balance')
      const data = res.data
      username.value = data.username || username.value
      isMember.value = data.is_member || false
      memberExpireAt.value = data.member_expire_at || null

      const pointsStore = usePointsStore()
      pointsStore.balance = data.points ?? pointsStore.balance
      pointsStore.isMember = data.is_member || false
      pointsStore.memberExpireAt = data.member_expire_at || null
    } catch (e) {
      console.error('Failed to fetch user info', e)
    }
  }

  return {
    username,
    token,
    isMember,
    memberExpireAt,
    isLoggedIn,
    login,
    register,
    logout,
    fetchUserInfo
  }
})
