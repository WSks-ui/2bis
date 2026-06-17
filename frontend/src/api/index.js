import axios from 'axios'
import { ElMessage } from '../services/toast'
import { clearStoredToken, getStoredToken } from '../services/authToken'

const api = axios.create({
  baseURL: '/api'
})

api.interceptors.request.use(
  (config) => {
    const token = getStoredToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = error.config?.url || ''
    const isAuthLogin = requestUrl.includes('/auth/login')
    if (error.response && error.response.status === 401 && !isAuthLogin) {
      clearStoredToken()
      ElMessage.error('登录已过期，请重新登录')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
