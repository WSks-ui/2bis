<template>
  <div class="auth-page">
    <section class="auth-showcase" aria-label="2Bis AI Image Studio">
      <div class="showcase-art">
        <img
          class="showcase-image"
          src="/auth/aria-showcase.webp"
          alt=""
          loading="eager"
          decoding="async"
          fetchpriority="high"
        />
        <img
          class="showcase-poster"
          src="/auth/aria-poster.webp"
          alt=""
          loading="eager"
          decoding="async"
        />
        <div class="art-frame frame-primary">
          <span class="frame-label">IMAGE / 01</span>
          <strong>Dreamlike light study</strong>
        </div>
        <div class="art-frame frame-secondary">
          <span class="frame-label">UPSCALE</span>
          <strong>3840 x 2160</strong>
        </div>
        <div class="art-grain"></div>
      </div>

      <router-link to="/" class="showcase-logo">2Bis</router-link>
      <div class="showcase-copy">
        <span class="eyebrow">AI Image Studio</span>
        <h1>把想象变成可交付的视觉作品。</h1>
        <p>从提示词到高清成片，2Bis 为创作者保留完整历史、额度与专业工作流。</p>
      </div>
    </section>

    <main
      ref="authPanelRef"
      class="auth-panel"
      @pointerenter="handleGridEnter"
      @pointermove="handleGridMove"
      @pointerleave="handleGridLeave"
    >
      <div class="auth-card">
        <div class="auth-heading">
          <span class="eyebrow">Welcome back</span>
          <h2>登录工作室</h2>
          <p>继续生成、管理和复用你的 AI 图像资产。</p>
        </div>

        <nav class="auth-tabs" aria-label="登录与注册切换">
          <span class="active">登录</span>
          <router-link to="/register">注册</router-link>
        </nav>

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
            <label class="remember-check">
              <input v-model="rememberMe" type="checkbox" />
              <span class="check-mark" aria-hidden="true"></span>
              <span>本机保持登录</span>
            </label>
            <button class="text-button" type="button" @click="showUnavailable('密码找回')">忘记密码？</button>
          </div>

          <button type="submit" class="btn-black btn-auth" :disabled="loading">
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </form>

        <div class="auth-divider">或继续使用</div>
        <div class="social-row" aria-label="第三方登录">
          <button type="button" @click="showUnavailable('Google 登录')" aria-label="Google 登录">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l3.66-2.84z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06L5.84 9.9C6.71 7.3 9.14 5.38 12 5.38z" />
            </svg>
            <span>Google</span>
          </button>
          <button type="button" @click="showUnavailable('Apple 登录')" aria-label="Apple 登录">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path fill="currentColor" d="M17.28 12.36c-.02-2.18 1.78-3.24 1.86-3.29-1.02-1.48-2.59-1.68-3.14-1.7-1.32-.14-2.6.79-3.27.79-.68 0-1.7-.77-2.81-.75-1.43.02-2.77.85-3.51 2.15-1.52 2.63-.39 6.5 1.07 8.63.73 1.04 1.58 2.2 2.69 2.16 1.09-.04 1.5-.69 2.81-.69 1.3 0 1.68.69 2.82.67 1.17-.02 1.91-1.04 2.61-2.09.84-1.19 1.18-2.36 1.19-2.42-.03-.01-2.3-.88-2.32-3.46zM15.14 5.97c.59-.74.99-1.74.88-2.76-.85.04-1.91.59-2.53 1.31-.55.64-1.04 1.69-.91 2.67.96.07 1.95-.48 2.56-1.22z" />
            </svg>
            <span>Apple</span>
          </button>
          <button type="button" @click="showUnavailable('SSO 登录')" aria-label="SSO 登录">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path fill="currentColor" d="M12 3.5a8.5 8.5 0 0 0-8.5 8.5h3a5.5 5.5 0 1 1 2.75 4.76l-1.5 2.6A8.5 8.5 0 1 0 12 3.5z" />
              <path fill="currentColor" d="M3 13.25h8.1L8.3 16.05l1.95 1.95L16.4 12l-6.15-6-1.95 1.95 2.8 2.8H3v2.5z" />
            </svg>
            <span>SSO</span>
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthGridInteraction } from '../composables/useAuthGridInteraction'
import { ElMessage } from '../services/toast'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const rememberMe = ref(true)
const { authPanelRef, handleGridEnter, handleGridMove, handleGridLeave } = useAuthGridInteraction()

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
    await userStore.login(form.username, form.password, { remember: rememberMe.value })
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
  position: relative;
  display: grid;
  grid-template-columns: minmax(420px, 58vw) minmax(380px, 1fr);
  background: #f8f7f2;
  overflow: hidden;
}

.auth-showcase {
  position: relative;
  min-height: 100vh;
  padding: clamp(28px, 4vw, 56px);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  isolation: isolate;
  overflow: hidden;
  color: #fff;
  background:
    linear-gradient(135deg, rgba(4, 7, 14, 0.94), rgba(18, 31, 48, 0.86)),
    url('/auth/aria-showcase-blur.webp') center / cover no-repeat;
}

.auth-showcase::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.68), transparent 86%);
}

.showcase-art {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  background: #030609 url('/auth/aria-showcase-blur.webp') center / cover no-repeat;
}

.showcase-art::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  background:
    radial-gradient(circle at 70% 34%, rgba(42, 119, 215, 0.14), transparent 22rem),
    radial-gradient(circle at 45% 62%, rgba(238, 180, 82, 0.18), transparent 20rem),
    linear-gradient(90deg, rgba(0, 0, 0, 0.5) 0%, rgba(0, 0, 0, 0.18) 46%, rgba(0, 0, 0, 0.48) 100%),
    linear-gradient(180deg, rgba(0, 0, 0, 0.34) 0%, transparent 42%, rgba(0, 0, 0, 0.72) 100%);
  pointer-events: none;
}

.showcase-art::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 3;
  background:
    linear-gradient(90deg, transparent calc(100% - clamp(55px, 4.5vw, 75px)), rgba(255, 253, 250, 0.34) calc(100% - clamp(37px, 3vw, 52px)), #fffdfa 100%),
    radial-gradient(circle at 50% 51%, transparent 0 28%, rgba(0, 0, 0, 0.18) 55%, rgba(0, 0, 0, 0.72) 100%),
    linear-gradient(115deg, rgba(255, 255, 255, 0.08), transparent 28%);
  pointer-events: none;
}

.showcase-image {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 52%;
  filter: saturate(1.08) contrast(1.04);
  transform: scale(1.035);
  will-change: transform;
  animation: showcase-drift 18s var(--ease-out-soft) infinite;
}

.showcase-poster {
  position: absolute;
  z-index: 4;
  right: clamp(30px, 5vw, 78px);
  top: clamp(96px, 14vh, 156px);
  width: min(230px, 23vw);
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 30px;
  box-shadow:
    0 34px 90px rgba(0, 0, 0, 0.48),
    0 0 0 8px rgba(255, 255, 255, 0.06);
  object-fit: cover;
  transform: rotate(2.5deg);
  animation: poster-float 9s ease-in-out infinite;
}

.art-frame {
  position: absolute;
  z-index: 5;
  width: min(270px, 28vw);
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 24px;
  background: rgba(8, 13, 20, 0.38);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.26);
  backdrop-filter: blur(24px);
  font-family: var(--font-ui);
}

.frame-primary {
  right: clamp(34px, 5.8vw, 90px);
  bottom: 13%;
}

.frame-secondary {
  left: clamp(34px, 6vw, 92px);
  top: 25%;
}

.frame-label {
  display: block;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.art-frame strong {
  display: block;
  max-width: 180px;
  font-size: 20px;
  line-height: 1.15;
}

.art-grain {
  position: absolute;
  inset: 0;
  opacity: 0.17;
  background-image:
    radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.9) 0 1px, transparent 1px),
    radial-gradient(circle at 72% 62%, rgba(255, 255, 255, 0.7) 0 1px, transparent 1px);
  background-size: 18px 18px, 23px 23px;
  mix-blend-mode: overlay;
}

.showcase-logo {
  position: relative;
  z-index: 6;
  width: fit-content;
  color: #fff;
  font-family: var(--font-heading);
  font-size: clamp(44px, 6vw, 82px);
  font-style: italic;
  font-weight: 950;
  line-height: 0.9;
  letter-spacing: -0.1em;
  text-shadow: 0 16px 42px rgba(0, 0, 0, 0.36);
}

.showcase-logo:hover {
  color: #fff;
}

.showcase-copy {
  position: relative;
  z-index: 6;
  max-width: 560px;
  padding-bottom: clamp(12px, 4vw, 48px);
}

.eyebrow {
  color: rgba(255, 255, 255, 0.72);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.showcase-copy h1 {
  margin: 14px 0 18px;
  color: #fff;
  font-size: clamp(42px, 6vw, 78px);
  line-height: 0.95;
  letter-spacing: -0.07em;
}

.showcase-copy p {
  max-width: 470px;
  color: rgba(255, 255, 255, 0.72);
  font-family: var(--font-ui);
  font-size: 16px;
  line-height: 1.8;
}

.auth-panel {
  min-height: 100vh;
  position: relative;
  z-index: 7;
  --grid-x: 50%;
  --grid-y: 50%;
  --grid-target-x: 50%;
  --grid-target-y: 50%;
  --grid-tail-x: 50%;
  --grid-tail-y: 50%;
  --grid-warp-x: 0px;
  --grid-warp-y: 0px;
  --grid-size: 42px;
  --grid-stretch-x: 1;
  --grid-stretch-y: 1;
  --grid-tilt: 0deg;
  --grid-softness: 132px;
  padding: clamp(24px, 5vw, 72px);
  display: grid;
  place-items: center;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(circle at 82% 14%, rgba(60, 110, 232, 0.1), transparent 18rem),
    linear-gradient(180deg, #fffdfa, #f6f4ef);
}

.auth-panel::before,
.auth-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.auth-panel::before {
  /* 右侧背景网格保持低对比度，避免抢走登录表单的视觉层级。 */
  opacity: 0.62;
  background-image:
    linear-gradient(90deg, rgba(32, 42, 57, 0.058) 1px, transparent 1px),
    linear-gradient(180deg, rgba(32, 42, 57, 0.05) 1px, transparent 1px);
  background-size: var(--grid-size) var(--grid-size);
  background-position: center;
  mask-image: radial-gradient(ellipse at 58% 46%, #000 0 58%, rgba(0, 0, 0, 0.5) 76%, transparent 100%);
}

.auth-panel::after {
  opacity: 0;
  background-image:
    radial-gradient(ellipse at var(--grid-target-x) var(--grid-target-y), rgba(60, 110, 232, 0.14), transparent 9rem),
    radial-gradient(ellipse at var(--grid-tail-x) var(--grid-tail-y), rgba(60, 110, 232, 0.11), transparent 7rem),
    linear-gradient(90deg, rgba(60, 110, 232, 0.2) 1px, transparent 1px),
    linear-gradient(180deg, rgba(60, 110, 232, 0.16) 1px, transparent 1px);
  background-size:
    100% 100%,
    100% 100%,
    var(--grid-size) var(--grid-size),
    var(--grid-size) var(--grid-size);
  background-position:
    0 0,
    0 0,
    calc(50% + var(--grid-warp-x)) calc(50% + var(--grid-warp-y)),
    calc(50% - var(--grid-warp-y)) calc(50% + var(--grid-warp-x));
  mask-image:
    radial-gradient(
      ellipse at var(--grid-x) var(--grid-y),
      #000 0 44px,
      rgba(0, 0, 0, 0.94) 78px,
      rgba(0, 0, 0, 0.38) calc(var(--grid-softness) - 34px),
      transparent var(--grid-softness)
    ),
    radial-gradient(
      ellipse at var(--grid-tail-x) var(--grid-tail-y),
      rgba(0, 0, 0, 0.72) 0 32px,
      rgba(0, 0, 0, 0.28) 86px,
      transparent calc(var(--grid-softness) - 12px)
    );
  mask-composite: add;
  mix-blend-mode: multiply;
  transform-origin: var(--grid-x) var(--grid-y);
  transform:
    translate3d(var(--grid-warp-x), var(--grid-warp-y), 0)
    rotate(var(--grid-tilt))
    scale(var(--grid-stretch-x), var(--grid-stretch-y));
  transition:
    opacity 220ms ease;
  will-change: opacity, transform, mask-image, background-position;
}

.auth-panel.is-grid-active::after {
  opacity: 0.76;
}

.auth-card {
  width: min(100%, 440px);
  position: relative;
  z-index: 1;
  padding: clamp(30px, 4vw, 44px);
  border: 1px solid rgba(226, 229, 223, 0.86);
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 24px 70px rgba(28, 28, 28, 0.1);
  backdrop-filter: blur(18px);
}

.auth-heading {
  margin-bottom: 24px;
}

.auth-heading .eyebrow {
  color: var(--color-blue);
}

.auth-heading h2 {
  margin: 8px 0 8px;
  font-size: 34px;
  letter-spacing: -0.05em;
}

.auth-heading p {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 14px;
}

.auth-tabs {
  margin-bottom: 26px;
  padding: 5px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  border: 1px solid var(--color-line);
  border-radius: 999px;
  background: #f3f4ef;
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 900;
}

.auth-tabs span,
.auth-tabs a {
  min-height: 38px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: var(--color-muted);
  transition:
    color var(--transition-base),
    background var(--transition-base),
    box-shadow var(--transition-base),
    transform var(--transition-base);
}

.auth-tabs a:hover {
  color: var(--color-ink);
  transform: translateY(-1px);
}

.auth-tabs .active {
  color: var(--color-ink);
  background: #fff;
  box-shadow: 0 8px 20px rgba(23, 23, 23, 0.08);
}

.auth-form {
  display: grid;
  gap: 18px;
}

.auth-form > label {
  display: grid;
  gap: 8px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 850;
}

.auth-input {
  width: 100%;
  min-height: 50px;
  padding: 0 16px;
  border: 1px solid transparent;
  border-radius: 16px;
  background: #f4f5f1;
  color: var(--color-ink);
  outline: none;
  box-shadow: inset 0 0 0 1px rgba(210, 214, 206, 0.9);
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base),
    background var(--transition-base),
    transform var(--transition-base);
}

.auth-input::placeholder {
  color: #a1a69f;
}

.auth-input:focus {
  border-color: rgba(60, 110, 232, 0.5);
  background: #fff;
  box-shadow:
    inset 0 0 0 1px rgba(60, 110, 232, 0.24),
    0 0 0 5px rgba(60, 110, 232, 0.1),
    0 14px 34px rgba(60, 110, 232, 0.08);
  transform: translateY(-1px);
}

.input-error {
  color: var(--color-red);
  font-size: 12px;
  font-weight: 800;
}

.form-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
}

.remember-check {
  width: fit-content;
  display: inline-flex;
  gap: 8px;
  align-items: center;
  color: var(--color-muted);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
}

.remember-check input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.check-mark {
  width: 18px;
  height: 18px;
  display: inline-grid;
  place-items: center;
  border: 1px solid var(--color-line-strong);
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 6px 12px rgba(23, 23, 23, 0.04);
  transition:
    border-color var(--transition-base),
    background var(--transition-base),
    box-shadow var(--transition-base),
    transform var(--transition-base);
}

.check-mark::after {
  content: '';
  width: 8px;
  height: 5px;
  border-left: 2px solid #fff;
  border-bottom: 2px solid #fff;
  opacity: 0;
  transform: rotate(-45deg) translateY(-1px) scale(0.7);
  transition:
    opacity var(--transition-base),
    transform var(--transition-base);
}

.remember-check input:checked + .check-mark {
  border-color: var(--color-blue);
  background: var(--color-blue);
  box-shadow: 0 8px 16px rgba(60, 110, 232, 0.22);
}

.remember-check input:checked + .check-mark::after {
  opacity: 1;
  transform: rotate(-45deg) translateY(-1px) scale(1);
}

.remember-check:hover .check-mark {
  transform: translateY(-1px);
}

.text-button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
  transition:
    color var(--transition-base),
    transform var(--transition-base);
}

.text-button:hover {
  color: var(--color-blue);
  transform: translateY(-1px);
}

.btn-auth {
  min-height: 52px;
  margin-top: 2px;
  border-radius: 16px;
  font-family: var(--font-ui);
  font-size: 15px;
  font-weight: 900;
}

.auth-divider {
  margin: 30px 0 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--color-soft);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
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
  min-height: 48px;
  display: inline-flex;
  justify-content: center;
  gap: 8px;
  align-items: center;
  border: 1px solid var(--color-line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 900;
  transition:
    border-color var(--transition-base),
    background var(--transition-base),
    transform var(--transition-base),
    box-shadow var(--transition-base);
}

.social-row svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}

.social-row button:hover {
  border-color: rgba(60, 110, 232, 0.24);
  background: #fff;
  box-shadow: 0 14px 28px rgba(23, 23, 23, 0.08);
  transform: translateY(-2px);
}

.social-row button:active {
  transform: translateY(0) scale(0.98);
}

@keyframes showcase-drift {
  0%, 100% {
    transform: scale(1.035) translate3d(0, 0, 0);
  }

  50% {
    transform: scale(1.075) translate3d(-1.2%, -1%, 0);
  }
}

@keyframes poster-float {
  0%, 100% {
    transform: rotate(2.5deg) translate3d(0, 0, 0);
  }

  50% {
    transform: rotate(1deg) translate3d(0, -12px, 0);
  }
}

@media (max-width: 980px) {
  .auth-page {
    grid-template-columns: 1fr;
  }

  .auth-showcase {
    min-height: 46vh;
  }

  .showcase-image {
    object-position: center 58%;
  }

  .showcase-art::after {
    background:
      linear-gradient(180deg, transparent calc(100% - 75px), rgba(255, 253, 250, 0.38) calc(100% - 45px), #fffdfa 100%),
      radial-gradient(circle at 50% 51%, transparent 0 28%, rgba(0, 0, 0, 0.18) 55%, rgba(0, 0, 0, 0.72) 100%),
      linear-gradient(115deg, rgba(255, 255, 255, 0.08), transparent 28%);
  }

  .showcase-poster,
  .art-frame {
    display: none;
  }

  .auth-panel {
    min-height: auto;
    padding: clamp(24px, 5vw, 72px);
    place-items: center;
  }

  .auth-panel::after {
    display: none;
  }

  .showcase-copy {
    padding-top: 120px;
  }
}

@media (max-width: 560px) {
  .auth-showcase {
    min-height: 42vh;
    padding: 24px;
  }

  .showcase-image {
    animation: none;
    transform: scale(1.02);
  }

  .showcase-copy h1 {
    font-size: 38px;
  }

  .auth-panel {
    padding: 18px;
  }

  .auth-card {
    padding: 24px;
    border-radius: 24px;
  }

  .form-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .social-row {
    grid-template-columns: 1fr;
  }
}

@media (hover: none), (pointer: coarse) {
  .auth-panel::after {
    display: none;
  }
}
</style>
