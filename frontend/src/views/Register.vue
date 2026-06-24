<template>
  <div class="auth-page auth-page-register">
    <section v-if="showShowcase" class="auth-showcase" aria-label="2Bis AI Image Studio">
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
          <span class="frame-label">WORKFLOW</span>
          <strong>Prompt to delivery</strong>
        </div>
        <div class="art-frame frame-secondary">
          <span class="frame-label">ARCHIVE</span>
          <strong>History saved</strong>
        </div>
        <div class="art-grain"></div>
      </div>

      <router-link to="/" class="showcase-logo" data-cursor="interactive">2Bis</router-link>
      <div class="showcase-copy">
        <span class="eyebrow">AI Image Studio</span>
        <h1>建立你的私人 AI 影像工作室。</h1>
        <p>注册后即可保存历史作品、管理订阅额度，并体验更稳定的专业工作流。</p>
      </div>
    </section>

    <main class="auth-panel">
      <div class="auth-card">
        <div class="auth-heading">
          <span class="eyebrow">Start creating</span>
          <h2>创建账号</h2>
          <p>用一个账号管理你的创作、额度和生成历史。</p>
        </div>

        <nav class="auth-tabs auth-tabs-register" aria-label="登录与注册切换">
          <router-link to="/login" data-cursor="interactive">登录</router-link>
          <span class="active" aria-current="page">注册</span>
        </nav>

        <form class="auth-form" @submit.prevent="handleRegister">
          <label class="field-line">
            用户名
            <input
              v-model="form.username"
              class="auth-input"
              placeholder="请输入用户名"
              autocomplete="username"
              :aria-invalid="String(Boolean(errors.username))"
              aria-describedby="register-username-error"
            />
            <span id="register-username-error" class="input-error" :class="{ 'is-visible': errors.username }">
              {{ errors.username || ' ' }}
            </span>
          </label>

          <label class="field-line">
            密码
            <input
              v-model="form.password"
              type="password"
              class="auth-input"
              placeholder="至少 6 位密码"
              autocomplete="new-password"
              :aria-invalid="String(Boolean(errors.password))"
              aria-describedby="register-password-error"
            />
            <span id="register-password-error" class="input-error" :class="{ 'is-visible': errors.password }">
              {{ errors.password || ' ' }}
            </span>
          </label>

          <label class="field-line">
            确认密码
            <input
              v-model="form.confirmPassword"
              type="password"
              class="auth-input"
              placeholder="请再次输入密码"
              autocomplete="new-password"
              :aria-invalid="String(Boolean(errors.confirmPassword))"
              aria-describedby="register-confirm-password-error"
            />
            <span
              id="register-confirm-password-error"
              class="input-error"
              :class="{ 'is-visible': errors.confirmPassword }"
            >
              {{ errors.confirmPassword || ' ' }}
            </span>
          </label>

          <button type="submit" class="btn-black btn-auth auth-primary-action" :disabled="loading" data-cursor="interactive">
            {{ loading ? '注册中…' : '创建账号' }}
          </button>
        </form>

        <p class="auth-note">注册即表示你同意以当前测试环境的计费规则使用体验积分与订阅额度。</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '../services/toast'
import { useUserStore } from '../stores/user'

defineOptions({ name: 'Register' })

defineProps({
  showShowcase: {
    type: Boolean,
    default: true
  }
})

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
  min-height: 100vh;
  position: relative;
  display: grid;
  grid-template-columns: minmax(420px, 58vw) minmax(380px, 1fr);
  background: #f8f7f2;
  overflow: hidden;
  animation: auth-page-settle 220ms var(--transition-slow) backwards;
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
  animation: auth-showcase-in 260ms var(--transition-slow) backwards;
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
    linear-gradient(
      90deg,
      transparent calc(100% - clamp(58px, 5vw, 86px)),
      rgba(255, 253, 250, 0.42) calc(100% - clamp(38px, 3.4vw, 58px)),
      #fffdfa 100%
    ),
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
  background:
    radial-gradient(circle at var(--grid-target-x) var(--grid-target-y), rgb(var(--auth-accent-rgb) / 0.13), transparent 16rem),
    radial-gradient(circle at 82% 14%, rgb(var(--auth-accent-rgb) / 0.11), transparent 18rem),
    radial-gradient(circle at 14% 88%, rgb(var(--auth-warm-rgb) / 0.1), transparent 18rem),
    linear-gradient(180deg, var(--auth-panel-bg-start), var(--auth-panel-bg-mid) 48%, var(--auth-panel-bg-end));
  isolation: isolate;
  overflow: hidden;
  transition: background 420ms var(--transition-slow);
}

.auth-panel::before,
.auth-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.auth-panel::before {
  z-index: -2;
  opacity: 0.62;
  background:
    linear-gradient(90deg, var(--auth-panel-line) 1px, transparent 1px),
    linear-gradient(180deg, var(--auth-panel-line) 1px, transparent 1px);
  background-size: var(--grid-size) var(--grid-size);
  background-position:
    calc(50% + var(--grid-warp-x)) calc(50% + var(--grid-warp-y)),
    calc(50% - var(--grid-warp-y)) calc(50% + var(--grid-warp-x));
  mask-image:
    radial-gradient(
      ellipse at var(--grid-x) var(--grid-y),
      rgba(0, 0, 0, 1) 0,
      rgba(0, 0, 0, 0.42) calc(var(--grid-softness) - 34px),
      transparent var(--grid-softness)
    ),
    radial-gradient(
      ellipse at var(--grid-tail-x) var(--grid-tail-y),
      rgba(0, 0, 0, 0.64) 0,
      transparent calc(var(--grid-softness) - 12px)
    );
  mask-composite: add;
  transform-origin: var(--grid-x) var(--grid-y);
  transform:
    translate3d(var(--grid-warp-x), var(--grid-warp-y), 0)
    rotate(var(--grid-tilt))
    scale(var(--grid-stretch-x), var(--grid-stretch-y));
  transition: opacity 180ms var(--transition-base);
  will-change: transform, opacity, background-position;
}

.auth-panel::after {
  z-index: -1;
  opacity: 0;
  background:
    radial-gradient(ellipse at var(--grid-target-x) var(--grid-target-y), rgb(var(--auth-accent-rgb) / 0.15), transparent 9rem),
    radial-gradient(ellipse at var(--grid-tail-x) var(--grid-tail-y), rgb(var(--auth-accent-rgb) / 0.12), transparent 7rem);
  transition: opacity 180ms var(--transition-base);
}

.auth-panel.is-grid-active::before {
  opacity: 0.88;
}

.auth-panel.is-grid-active::after {
  opacity: 1;
}

.auth-card {
  position: relative;
  width: min(100%, 440px);
  padding: clamp(30px, 4vw, 44px);
  border: 1px solid rgba(226, 229, 223, 0.86);
  border-radius: 32px;
  background:
    linear-gradient(180deg, var(--auth-card-bg), rgba(255, 255, 255, 0.72)),
    radial-gradient(circle at 18% 0%, rgb(var(--auth-accent-rgb) / 0.08), transparent 16rem);
  box-shadow:
    0 24px 70px rgba(28, 28, 28, 0.1),
    0 0 0 1px var(--auth-panel-shadow);
  backdrop-filter: blur(18px);
  animation: auth-card-in 260ms 50ms var(--transition-slow) backwards;
}

.auth-heading {
  margin-bottom: 24px;
}

.auth-heading .eyebrow {
  color: rgb(var(--auth-accent-rgb));
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
  background: var(--auth-control-bg-strong);
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
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 8px 20px var(--auth-panel-shadow);
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
  background: var(--auth-control-bg);
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
  border-color: rgb(var(--auth-accent-rgb) / 0.5);
  background: #fff;
  box-shadow:
    inset 0 0 0 1px rgb(var(--auth-accent-rgb) / 0.24),
    0 0 0 5px rgb(var(--auth-accent-rgb) / 0.1),
    0 14px 34px rgb(var(--auth-accent-rgb) / 0.08);
  transform: translateY(-1px);
}

.input-error {
  color: var(--color-red);
  font-size: 12px;
  font-weight: 800;
}

.btn-auth {
  min-height: 52px;
  margin-top: 2px;
  border-radius: 16px;
  font-family: var(--font-ui);
  font-size: 15px;
  font-weight: 900;
}

.auth-note {
  margin: 22px 0 0;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.7;
  text-align: center;
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

@keyframes auth-page-settle {
  from {
    opacity: 0;
    transform: translate3d(0, 8px, 0);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes auth-showcase-in {
  from {
    filter: saturate(0.8) brightness(0.9);
  }

  to {
    filter: saturate(1) brightness(1);
  }
}

@keyframes auth-card-in {
  from {
    opacity: 0;
    transform: translate3d(16px, 0, 0) scale(0.985);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
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

  .showcase-poster,
  .art-frame {
    display: none;
  }

  .auth-panel {
    min-height: auto;
  }

  .auth-page-register .auth-panel {
    grid-column: 1;
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
}
</style>
