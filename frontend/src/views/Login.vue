<template>
  <div class="auth-page paper-page">
    <section class="auth-brand-panel">
      <router-link to="/" class="auth-logo">2Bis</router-link>
      <h1>AI Image Studio</h1>
      <p>智能生成、专业创作、无限可能。</p>
      <div class="leaf leaf-one"></div>
      <div class="leaf leaf-two"></div>
      <div class="leaf leaf-three"></div>
    </section>

    <section class="auth-card surface-card">
      <div class="auth-tabs">
        <span class="active">登录</span>
        <router-link to="/register">注册</router-link>
      </div>

      <form class="auth-form" @submit.prevent="handleLogin">
        <label>
          邮箱 / 用户名
          <input
            v-model="form.username"
            class="auth-input"
            placeholder="请输入用户名"
            autocomplete="username"
          />
          <span v-if="errors.username" class="input-error">{{ errors.username }}</span>
        </label>

        <label>
          密码
          <input
            v-model="form.password"
            type="password"
            class="auth-input"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
          <span v-if="errors.password" class="input-error">{{ errors.password }}</span>
        </label>

        <div class="form-row">
          <span class="session-note">本机保持登录</span>
          <button class="text-button" type="button" @click="showUnavailable('密码找回')">忘记密码？</button>
        </div>

        <button type="submit" class="btn-black btn-auth" :disabled="loading">
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </form>

      <div class="auth-divider">或继续使用</div>
      <div class="social-row">
        <button type="button" @click="showUnavailable('Google 登录')">G</button>
        <button type="button" @click="showUnavailable('Apple 登录')">Apple</button>
        <button type="button" @click="showUnavailable('SSO 登录')">SSO</button>
      </div>
    </section>
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
  password: ''
})

const errors = reactive({
  username: '',
  password: ''
})

function validate() {
  errors.username = ''
  errors.password = ''
  let valid = true
  if (!form.username.trim()) {
    errors.username = '请输入用户名'
    valid = false
  }
  if (!form.password) {
    errors.password = '请输入密码'
    valid = false
  }
  return valid
}

async function handleLogin() {
  if (!validate()) return

  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(loginErrorMessage(e))
  } finally {
    loading.value = false
  }
}

function loginErrorMessage(e) {
  const detail = e.response?.data?.detail
  if (e.response?.status === 401 || detail === 'Invalid username or password') {
    return '用户名或密码错误'
  }
  return detail || '登录失败，请检查用户名和密码'
}

function showUnavailable(name) {
  ElMessage.info(`${name}暂未开放，请先使用账号密码登录`)
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: 48px;
  display: grid;
  grid-template-columns: minmax(320px, 1.1fr) minmax(340px, 460px);
  gap: 48px;
  align-items: center;
}

.auth-brand-panel {
  position: relative;
  min-height: 560px;
  display: grid;
  place-items: center;
  align-content: center;
  overflow: hidden;
  border: 1px solid var(--color-line);
  border-radius: 34px;
  background:
    radial-gradient(circle at 30% 26%, rgba(255, 255, 255, 0.9), transparent 12rem),
    linear-gradient(135deg, rgba(222, 229, 217, 0.78), rgba(246, 247, 243, 0.76));
  box-shadow: var(--shadow-md);
  text-align: center;
}

.auth-logo {
  color: var(--color-ink);
  font-family: var(--font-heading);
  font-size: clamp(64px, 10vw, 116px);
  font-style: italic;
  font-weight: 900;
  letter-spacing: -0.09em;
}

.auth-brand-panel h1 {
  margin: -10px 0 0;
  font-size: clamp(26px, 4vw, 46px);
  letter-spacing: -0.04em;
}

.auth-brand-panel p {
  margin: 12px 0 0;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 15px;
  font-weight: 650;
}

.leaf {
  position: absolute;
  border: 1px solid rgba(91, 122, 94, 0.18);
  border-radius: 100% 0 100% 0;
  background: rgba(101, 138, 104, 0.16);
  transform: rotate(22deg);
}

.leaf-one {
  left: 11%;
  bottom: 18%;
  width: 96px;
  height: 168px;
}

.leaf-two {
  left: 19%;
  bottom: 8%;
  width: 68px;
  height: 128px;
  transform: rotate(-18deg);
}

.leaf-three {
  right: 12%;
  top: 14%;
  width: 72px;
  height: 128px;
  transform: rotate(42deg);
}

.auth-card {
  padding: 36px;
}

.auth-tabs {
  margin-bottom: 30px;
  display: flex;
  justify-content: center;
  gap: 54px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 18px;
  font-weight: 850;
}

.auth-tabs span,
.auth-tabs a {
  position: relative;
  color: inherit;
}

.auth-tabs .active {
  color: var(--color-ink);
}

.auth-tabs .active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -12px;
  height: 3px;
  border-radius: 999px;
  background: var(--color-ink);
}

.auth-form {
  display: grid;
  gap: 18px;
}

.auth-form label {
  display: grid;
  gap: 8px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 800;
}

.auth-input {
  width: 100%;
  min-height: 46px;
  padding: 0 14px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.78);
  color: var(--color-ink);
  outline: none;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.auth-input:focus {
  border-color: var(--color-blue);
  box-shadow: 0 0 0 4px rgba(60, 110, 232, 0.08);
}

.input-error {
  color: var(--color-red);
  font-size: 12px;
}

.form-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
}

.text-button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.text-button:hover {
  color: var(--color-ink);
}

.session-note {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.btn-auth {
  min-height: 48px;
  margin-top: 4px;
  font-family: var(--font-ui);
  font-size: 15px;
  font-weight: 850;
}

.auth-divider {
  margin: 28px 0 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--color-soft);
  font-family: var(--font-ui);
  font-size: 12px;
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: var(--color-line);
}

.social-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.social-row button {
  min-height: 44px;
  border: 1px solid var(--color-line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-weight: 850;
}

@media (max-width: 900px) {
  .auth-page {
    grid-template-columns: 1fr;
    padding: 24px;
  }

  .auth-brand-panel {
    min-height: 320px;
  }
}

@media (max-width: 520px) {
  .auth-page {
    padding: 14px;
  }

  .auth-card {
    padding: 24px;
  }

  .social-row {
    grid-template-columns: 1fr;
  }
}
</style>
