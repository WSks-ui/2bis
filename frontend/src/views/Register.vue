<template>
  <div class="auth-page">
    <div class="auth-bg-glow"></div>

    <div class="auth-card">
      <router-link to="/" class="auth-brand">
        <span class="brand-icon">◇</span>
        <span class="brand-text">2Bis</span>
      </router-link>

      <h1 class="auth-title">创建账号</h1>
      <p class="auth-subtitle">注册后即可开始 AI 创作之旅</p>

      <form class="auth-form" @submit.prevent="handleRegister">
        <div class="input-group">
          <label class="input-label">用户名</label>
          <input
            v-model="form.username"
            class="auth-input"
            placeholder="请输入用户名"
            autocomplete="username"
          />
          <p v-if="errors.username" class="input-error">{{ errors.username }}</p>
        </div>

        <div class="input-group">
          <label class="input-label">密码</label>
          <input
            v-model="form.password"
            type="password"
            class="auth-input"
            placeholder="至少 6 位密码"
            autocomplete="new-password"
          />
          <p v-if="errors.password" class="input-error">{{ errors.password }}</p>
        </div>

        <div class="input-group">
          <label class="input-label">确认密码</label>
          <input
            v-model="form.confirmPassword"
            type="password"
            class="auth-input"
            placeholder="请再次输入密码"
            autocomplete="new-password"
          />
          <p v-if="errors.confirmPassword" class="input-error">{{ errors.confirmPassword }}</p>
        </div>

        <button
          type="submit"
          class="btn-auth"
          :disabled="loading"
        >
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '注册中…' : '注册' }}
        </button>
      </form>

      <p class="auth-switch">
        已有账号？
        <router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const errors = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

function validate() {
  errors.username = ''
  errors.password = ''
  errors.confirmPassword = ''
  let valid = true

  if (!form.username.trim()) {
    errors.username = '请输入用户名'
    valid = false
  }
  if (!form.password) {
    errors.password = '请输入密码'
    valid = false
  } else if (form.password.length < 6) {
    errors.password = '密码长度不能少于 6 位'
    valid = false
  }
  if (!form.confirmPassword) {
    errors.confirmPassword = '请再次输入密码'
    valid = false
  } else if (form.password !== form.confirmPassword) {
    errors.confirmPassword = '两次输入的密码不一致'
    valid = false
  }

  return valid
}

async function handleRegister() {
  if (!validate()) return

  loading.value = true
  try {
    await userStore.register(form.username, form.password)
    router.push('/login')
  } catch (e) {
    const msg = e.response?.data?.detail || '注册失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  position: relative;
  overflow: hidden;
}

.auth-bg-glow {
  position: absolute;
  top: -30%;
  right: -20%;
  width: 70%;
  height: 140%;
  background: radial-gradient(ellipse at center, rgba(106, 155, 204, 0.07) 0%, transparent 70%);
  pointer-events: none;
  animation: glow-pulse 6s ease-in-out infinite alternate;
}

@keyframes glow-pulse {
  from { opacity: 0.6; transform: scale(1); }
  to { opacity: 1; transform: scale(1.1); }
}

.auth-card {
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: 48px 40px;
  background: rgba(232, 230, 220, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.08);
  border-radius: var(--radius-xl);
  backdrop-filter: blur(10px);
  animation: card-reveal 0.5s ease-out;
}

@keyframes card-reveal {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-decoration: none;
  margin-bottom: 32px;
}

.brand-icon {
  font-size: 24px;
  color: var(--color-orange);
  transform: rotate(45deg);
  display: inline-block;
  animation: brand-spin 20s linear infinite;
}

.brand-text {
  font-family: var(--font-heading);
  font-size: 26px;
  font-weight: 800;
  color: var(--color-light);
  letter-spacing: -0.04em;
}

.auth-title {
  font-size: 28px;
  margin-bottom: 8px;
  text-align: center;
}

.auth-subtitle {
  font-size: 15px;
  color: var(--color-mid);
  text-align: center;
  margin-bottom: 36px;
  font-style: italic;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  animation: form-in 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}
.input-group:nth-child(1) { animation-delay: 0.12s; }
.input-group:nth-child(2) { animation-delay: 0.19s; }
.input-group:nth-child(3) { animation-delay: 0.26s; }

@keyframes form-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.input-label {
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-mid);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.auth-input {
  width: 100%;
  padding: 14px 16px;
  background: rgba(250, 249, 245, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-md);
  color: var(--color-light);
  font-family: var(--font-body);
  font-size: 15px;
  outline: none;
  transition: all var(--transition-base);
}

.auth-input::placeholder {
  color: var(--color-mid);
  opacity: 0.5;
  font-style: italic;
}

.auth-input:focus {
  border-color: var(--color-orange);
  box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.12);
  background: rgba(250, 249, 245, 0.06);
}

.input-error {
  font-family: var(--font-heading);
  font-size: 12px;
  color: var(--color-orange);
  margin: 0;
}

.btn-auth {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 14px;
  background: var(--color-orange);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-dark);
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  margin-top: 8px;
  animation: btn-in 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
  animation-delay: 0.35s;
}

@keyframes btn-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.btn-auth:hover:not(:disabled) {
  background: #c8694a;
  box-shadow: 0 4px 20px rgba(217, 119, 87, 0.3);
  transform: translateY(-1px);
}

.btn-auth:not(:disabled):active {
  transform: scale(0.96);
  transition: all 0.1s ease;
}

.btn-auth:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid transparent;
  border-top-color: var(--color-dark);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.auth-switch {
  text-align: center;
  margin-top: 28px;
  font-size: 14px;
  color: var(--color-mid);
  animation: auth-switch-in 0.5s ease 0.4s both;
}

@keyframes auth-switch-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.auth-switch a {
  font-weight: 600;
  margin-left: 4px;
}

@media (max-width: 480px) {
  .auth-card {
    padding: 36px 24px;
  }
}
</style>
