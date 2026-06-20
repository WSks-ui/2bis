<template>
  <div
    ref="authGridRef"
    class="auth-switch-host"
    :class="{
      'is-login-mode': isLogin,
      'is-register-mode': isRegister,
      'is-grid-active': isGridActive,
      'is-developing': isDeveloping,
      'develop-to-register': isDeveloping && developDirection === 'to-register',
      'develop-to-login': isDeveloping && developDirection === 'to-login'
    }"
    @pointerenter="handleGridEnter"
    @pointermove="handleGridMove"
    @pointerleave="handleGridLeave"
  >
    <div class="auth-canvas" aria-hidden="true">
      <img
        v-if="activeScene.preview"
        class="auth-canvas-image auth-canvas-preview"
        :src="activeScene.preview"
        alt=""
        decoding="async"
      />
      <img
        :key="activeScene.image"
        class="auth-canvas-image auth-canvas-primary"
        :src="activeScene.image"
        alt=""
        decoding="async"
        fetchpriority="high"
      />
      <div class="auth-canvas-grid"></div>
      <div class="auth-canvas-vignette"></div>
      <div class="auth-canvas-stars">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>

    <main class="auth-shell" aria-label="2Bis 登录与注册">
      <section class="auth-intro" aria-label="2Bis">
        <div class="intro-mark" aria-hidden="true">
          <span class="intro-mark-core"></span>
        </div>
        <span class="intro-kicker">AI IMAGE STUDIO</span>
        <h1>2Bis</h1>
        <p>继续管理你的提示词、成片资产、生成历史与体验额度。</p>
        <div class="intro-badges" aria-hidden="true">
          <span><i></i> 服务在线</span>
          <span>创作队列就绪</span>
        </div>
      </section>

      <section class="auth-workbench" aria-label="账户入口">
        <div class="workbench-shadow" aria-hidden="true"></div>
        <div class="auth-exposure-layer" aria-hidden="true">
          <span class="exposure-paper"></span>
          <span class="exposure-sweep"></span>
          <span class="exposure-line"></span>
        </div>

        <Login
          class="auth-pane"
          :show-showcase="false"
          :class="{ 'is-active': isLogin, 'is-inactive': !isLogin }"
          :aria-hidden="String(!isLogin)"
        />
        <Register
          class="auth-pane"
          :show-showcase="false"
          :class="{ 'is-active': isRegister, 'is-inactive': !isRegister }"
          :aria-hidden="String(!isRegister)"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthGridInteraction } from '../composables/useAuthGridInteraction'
import { AUTH_FALLBACK_SCENES, getAuthShowcaseScenes, preloadAuthImages } from '../utils/authAssets'
import Login from './Login.vue'
import Register from './Register.vue'

defineOptions({ name: 'AuthView' })

const route = useRoute()
const isRegister = computed(() => route.name === 'Register')
const isLogin = computed(() => !isRegister.value)
const authRouteNames = new Set(['Login', 'Register'])
const DEVELOP_TRANSITION_MS = 760
const SCENE_ROTATION_MS = 14000
const isDeveloping = ref(false)
const developDirection = ref('to-register')
const authScenes = ref(AUTH_FALLBACK_SCENES)
const sceneIndex = ref(0)
const activeScene = computed(() => authScenes.value[sceneIndex.value] || AUTH_FALLBACK_SCENES[0])
const {
  authPanelRef: authGridRef,
  handleGridEnter,
  handleGridMove,
  handleGridLeave,
  isGridActive
} = useAuthGridInteraction()
let developTimer = 0
let sceneTimer = 0

watch(
  () => route.name,
  (nextName, previousName) => {
    if (!authRouteNames.has(nextName) || !authRouteNames.has(previousName) || nextName === previousName) return

    developDirection.value = nextName === 'Register' ? 'to-register' : 'to-login'
    startDevelopTransition()
  },
  { flush: 'sync' }
)

onMounted(loadAuthScenes)
onBeforeUnmount(() => {
  clearDevelopTimer()
  clearSceneTimer()
})

async function loadAuthScenes() {
  const scenes = await getAuthShowcaseScenes()
  authScenes.value = scenes.length ? scenes : AUTH_FALLBACK_SCENES
  sceneIndex.value = randomIndex(authScenes.value.length)
  preloadAuthImages(authScenes.value)
  startSceneRotation()
}

function startSceneRotation() {
  clearSceneTimer()
  if (authScenes.value.length < 2) return

  sceneTimer = window.setInterval(() => {
    // 多图时避免连续抽到同一张，让未来新增作品后切换感稳定可见。
    const nextIndex = randomIndex(authScenes.value.length - 1)
    sceneIndex.value = nextIndex >= sceneIndex.value ? nextIndex + 1 : nextIndex
  }, SCENE_ROTATION_MS)
}

function randomIndex(length) {
  if (length <= 1) return 0
  return Math.floor(Math.random() * length)
}

function startDevelopTransition() {
  // 切换保留“显影”概念，但改成冷白曝光扫描，避免红色安全灯氛围干扰整体观感。
  clearDevelopTimer()
  isDeveloping.value = true
  developTimer = window.setTimeout(() => {
    isDeveloping.value = false
    developTimer = 0
  }, DEVELOP_TRANSITION_MS)
}

function clearDevelopTimer() {
  if (!developTimer) return
  window.clearTimeout(developTimer)
  developTimer = 0
}

function clearSceneTimer() {
  if (!sceneTimer) return
  window.clearInterval(sceneTimer)
  sceneTimer = 0
}
</script>

<style scoped>
.auth-switch-host {
  position: relative;
  box-sizing: border-box;
  min-height: 100vh;
  min-height: 100svh;
  --auth-accent-rgb: 72 147 90;
  --auth-success-rgb: 72 147 90;
  --auth-page-ink: #182219;
  --auth-page-muted: rgb(48 61 52 / 0.86);
  --auth-card-bg: rgb(255 255 255 / 0.88);
  --auth-control-bg: hsl(134deg 10% 94%);
  --auth-control-bg-strong: hsl(134deg 9% 91%);
  --auth-panel-line: rgb(34 61 43 / 0.36);
  --auth-panel-shadow: rgb(72 147 90 / 0.16);
  --develop-duration: 760ms;
  --grid-x: 50%;
  --grid-y: 50%;
  --grid-target-x: 50%;
  --grid-target-y: 50%;
  --grid-tail-x: 50%;
  --grid-tail-y: 50%;
  --grid-warp-x: 0px;
  --grid-warp-y: 0px;
  --grid-size: 58px;
  --grid-stretch-x: 1;
  --grid-stretch-y: 1;
  --grid-tilt: 0deg;
  --grid-softness: 164px;
  display: grid;
  place-items: center;
  overflow-x: hidden;
  overflow-y: auto;
  padding: clamp(28px, 5vw, 72px) 20px;
  background: linear-gradient(135deg, #f8faf5 0%, #eef5f1 48%, #f2f5f9 100%);
  color: var(--auth-page-ink);
}

.auth-canvas,
.auth-canvas::before,
.auth-canvas::after,
.auth-canvas-image,
.auth-canvas-grid,
.auth-canvas-vignette,
.auth-canvas-stars {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.auth-canvas {
  z-index: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 78% 18%, rgb(255 255 255 / 0.22), transparent 24rem),
    radial-gradient(circle at 18% 78%, rgb(var(--auth-accent-rgb) / 0.08), transparent 28rem),
    linear-gradient(135deg, #e6eee7 0%, #dce8e1 48%, #e1e7ef 100%);
}

.auth-canvas::before {
  content: '';
  z-index: 5;
  background:
    linear-gradient(90deg, rgb(244 248 242 / 0.2), rgb(244 248 242 / 0.04) 42%, rgb(238 245 240 / 0.12) 100%),
    linear-gradient(180deg, rgb(255 255 255 / 0.14), rgb(255 255 255 / 0.02) 44%, rgb(229 238 232 / 0.14));
}

.auth-canvas::after {
  content: '';
  z-index: 7;
  opacity: 0.08;
  background-image:
    radial-gradient(circle, rgb(30 47 36 / 0.22) 0 0.55px, transparent 0.75px),
    radial-gradient(circle, rgb(255 255 255 / 0.72) 0 0.5px, transparent 0.75px);
  background-position: 0 0, 2px 3px;
  background-size: 7px 7px, 9px 9px;
  mix-blend-mode: multiply;
}

.auth-canvas-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

.auth-canvas-preview {
  z-index: 1;
  transform: scale(1.08);
  filter: blur(30px) saturate(0.92) brightness(0.94);
  opacity: 0.46;
}

.auth-canvas-primary {
  z-index: 2;
  transform: scale(1.04);
  filter: saturate(1.08) contrast(1.05) brightness(0.94);
  opacity: 0.98;
  -webkit-mask-image: linear-gradient(90deg, rgb(0 0 0 / 0.56), rgb(0 0 0 / 0.98) 44%, rgb(0 0 0 / 0.9));
  mask-image: linear-gradient(90deg, rgb(0 0 0 / 0.56), rgb(0 0 0 / 0.98) 44%, rgb(0 0 0 / 0.9));
}

.auth-canvas-grid {
  z-index: 8;
  overflow: hidden;
  background-image:
    linear-gradient(rgb(20 39 25 / 0.14) 1px, transparent 1px),
    linear-gradient(90deg, rgb(20 39 25 / 0.12) 1px, transparent 1px),
    linear-gradient(rgb(247 255 249 / 0.13) 1px, transparent 1px),
    linear-gradient(90deg, rgb(247 255 249 / 0.1) 1px, transparent 1px);
  background-position: 50% 50%, 50% 50%, 0 0, 0 0;
  background-size:
    var(--grid-size) var(--grid-size),
    var(--grid-size) var(--grid-size),
    calc(var(--grid-size) * 0.5) calc(var(--grid-size) * 0.5),
    calc(var(--grid-size) * 0.5) calc(var(--grid-size) * 0.5);
  opacity: 0.52;
  mix-blend-mode: normal;
}

.auth-canvas-grid::before,
.auth-canvas-grid::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.auth-canvas-grid::before {
  z-index: 1;
  background-image:
    linear-gradient(90deg, rgb(33 66 43 / 0.38) 1px, transparent 1px),
    linear-gradient(180deg, rgb(33 66 43 / 0.34) 1px, transparent 1px),
    linear-gradient(90deg, rgb(246 255 248 / 0.26) 1px, transparent 1px),
    linear-gradient(180deg, rgb(246 255 248 / 0.22) 1px, transparent 1px);
  background-size:
    var(--grid-size) var(--grid-size),
    var(--grid-size) var(--grid-size),
    calc(var(--grid-size) * 0.5) calc(var(--grid-size) * 0.5),
    calc(var(--grid-size) * 0.5) calc(var(--grid-size) * 0.5);
  background-position:
    calc(50% + var(--grid-warp-x)) calc(50% + var(--grid-warp-y)),
    calc(50% - var(--grid-warp-y)) calc(50% + var(--grid-warp-x)),
    calc(50% + var(--grid-warp-x)) calc(50% + var(--grid-warp-y)),
    calc(50% - var(--grid-warp-y)) calc(50% + var(--grid-warp-x));
  opacity: 0.34;
  -webkit-mask-image:
    radial-gradient(
      ellipse at var(--grid-x) var(--grid-y),
      rgb(0 0 0) 0,
      rgb(0 0 0 / 0.58) calc(var(--grid-softness) - 34px),
      transparent var(--grid-softness)
    ),
    radial-gradient(
      ellipse at var(--grid-tail-x) var(--grid-tail-y),
      rgb(0 0 0 / 0.58) 0,
      transparent calc(var(--grid-softness) - 10px)
    );
  mask-image:
    radial-gradient(
      ellipse at var(--grid-x) var(--grid-y),
      rgb(0 0 0) 0,
      rgb(0 0 0 / 0.58) calc(var(--grid-softness) - 34px),
      transparent var(--grid-softness)
    ),
    radial-gradient(
      ellipse at var(--grid-tail-x) var(--grid-tail-y),
      rgb(0 0 0 / 0.58) 0,
      transparent calc(var(--grid-softness) - 10px)
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

.auth-canvas-grid::after {
  z-index: 2;
  opacity: 0.28;
  background:
    radial-gradient(ellipse at var(--grid-target-x) var(--grid-target-y), rgb(248 255 250 / 0.24), transparent 18rem),
    radial-gradient(ellipse at var(--grid-x) var(--grid-y), rgb(var(--auth-accent-rgb) / 0.16), transparent 13rem),
    radial-gradient(ellipse at var(--grid-tail-x) var(--grid-tail-y), rgb(22 54 35 / 0.12), transparent 10rem);
  mix-blend-mode: screen;
  transition: opacity 180ms var(--transition-base);
}

.auth-switch-host.is-grid-active .auth-canvas-grid::before {
  opacity: 0.78;
}

.auth-switch-host.is-grid-active .auth-canvas-grid::after {
  opacity: 0.66;
}

.auth-canvas-vignette {
  z-index: 6;
  background:
    radial-gradient(ellipse at 52% 48%, transparent 0 50%, rgb(255 255 255 / 0.04) 78%, rgb(226 235 229 / 0.16) 100%),
    linear-gradient(90deg, rgb(244 248 242 / 0.18) 0%, transparent 38%, rgb(244 248 242 / 0.06) 100%);
}

.auth-canvas-stars {
  z-index: 9;
  opacity: 0.12;
}

.auth-canvas-stars span {
  position: absolute;
  width: 14px;
  height: 14px;
  opacity: 0.12;
}

.auth-canvas-stars span::before,
.auth-canvas-stars span::after {
  content: '';
  position: absolute;
  inset: 50% auto auto 50%;
  border-radius: 999px;
  background: rgb(47 76 58 / 0.46);
  transform: translate(-50%, -50%);
}

.auth-canvas-stars span::before {
  width: 2px;
  height: 10px;
}

.auth-canvas-stars span::after {
  width: 10px;
  height: 2px;
}

.auth-canvas-stars span:nth-child(1) {
  top: 22%;
  left: 10%;
}

.auth-canvas-stars span:nth-child(2) {
  top: 18%;
  left: 34%;
  opacity: 0.32;
}

.auth-canvas-stars span:nth-child(3) {
  top: 28%;
  right: 12%;
  opacity: 0.38;
}

.auth-canvas-stars span:nth-child(4) {
  bottom: 20%;
  left: 18%;
  opacity: 0.24;
}

.auth-canvas-stars span:nth-child(5) {
  right: 34%;
  bottom: 16%;
  opacity: 0.28;
}

.auth-shell {
  position: relative;
  z-index: 10;
  width: min(100%, 1120px);
  display: grid;
  grid-template-columns: minmax(300px, 0.95fr) minmax(380px, 440px);
  gap: clamp(42px, 6vw, 86px);
  align-items: center;
}

.auth-intro {
  min-width: 0;
  position: relative;
  display: grid;
  justify-items: start;
  max-width: 520px;
  color: var(--auth-page-ink);
  isolation: isolate;
}

.auth-intro::before {
  content: '';
  position: absolute;
  inset: -34px -54px -36px -30px;
  z-index: -1;
  border-radius: 32px;
  background: radial-gradient(ellipse at 22% 48%, rgb(255 255 255 / 0.26), rgb(255 255 255 / 0.08) 58%, transparent 78%);
  filter: blur(12px);
}

.intro-mark {
  width: 58px;
  height: 58px;
  margin-bottom: 28px;
  display: grid;
  place-items: center;
  border: 1px solid rgb(var(--auth-accent-rgb) / 0.26);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgb(255 255 255 / 0.94), rgb(246 249 244 / 0.76)),
    radial-gradient(circle at 50% 35%, rgb(var(--auth-accent-rgb) / 0.18), transparent 72%);
  box-shadow:
    0 18px 46px rgb(45 68 52 / 0.16),
    inset 0 1px 0 rgb(255 255 255 / 0.72);
}

.intro-mark-core {
  position: relative;
  width: 22px;
  height: 22px;
  color: rgb(var(--auth-accent-rgb) / 0.9);
}

.intro-mark-core::before,
.intro-mark-core::after {
  content: '';
  position: absolute;
  inset: 50% auto auto 50%;
  border-radius: 999px;
  background: currentColor;
  transform: translate(-50%, -50%);
}

.intro-mark-core::before {
  width: 3px;
  height: 22px;
  box-shadow:
    8px 0 0 rgb(var(--auth-accent-rgb) / 0.22),
    -8px 0 0 rgb(var(--auth-accent-rgb) / 0.22);
}

.intro-mark-core::after {
  width: 22px;
  height: 3px;
  box-shadow:
    0 8px 0 rgb(var(--auth-accent-rgb) / 0.22),
    0 -8px 0 rgb(var(--auth-accent-rgb) / 0.22);
}

.intro-kicker {
  margin-bottom: 14px;
  color: rgb(var(--auth-accent-rgb) / 0.9);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.auth-intro h1 {
  margin: 0;
  color: #1b241d;
  font-family: var(--font-heading);
  font-size: clamp(68px, 8vw, 112px);
  font-style: italic;
  font-weight: 950;
  line-height: 0.9;
  letter-spacing: 0;
  text-shadow:
    0 18px 56px rgb(255 255 255 / 0.9),
    0 1px 0 rgb(255 255 255 / 0.74);
}

.auth-intro p {
  max-width: 520px;
  margin: 24px 0 0;
  color: var(--auth-page-muted);
  font-family: var(--font-ui);
  font-size: 16px;
  font-weight: 760;
  line-height: 1.75;
}

.intro-badges {
  margin-top: 28px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.intro-badges span {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border: 1px solid rgb(var(--auth-accent-rgb) / 0.22);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.68);
  color: rgb(38 52 41 / 0.86);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 880;
  box-shadow:
    0 10px 28px rgb(42 62 48 / 0.08),
    inset 0 1px 0 rgb(255 255 255 / 0.72);
}

.intro-badges i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgb(var(--auth-success-rgb));
  box-shadow: 0 0 18px rgb(var(--auth-success-rgb) / 0.38);
}

.auth-workbench {
  position: relative;
  width: 100%;
  isolation: isolate;
}

.workbench-shadow {
  position: absolute;
  inset: 8% -8% -10%;
  z-index: -1;
  border-radius: 24px;
  background:
    radial-gradient(ellipse at 50% 0%, rgb(255 255 255 / 0.72), transparent 58%),
    radial-gradient(ellipse at 50% 58%, rgb(var(--auth-accent-rgb) / 0.13), transparent 70%);
  filter: blur(28px);
}

.auth-exposure-layer {
  position: absolute;
  inset: -12px;
  z-index: 12;
  overflow: hidden;
  border-radius: 24px;
  opacity: 0;
  pointer-events: none;
}

.auth-switch-host.is-developing .auth-exposure-layer {
  animation: exposure-layer var(--develop-duration) var(--ease-out-soft) both;
}

.auth-exposure-layer span {
  position: absolute;
  inset: 0;
  opacity: 0;
}

.exposure-paper {
  background:
    radial-gradient(ellipse at 50% 42%, rgb(255 255 255 / 0.34), transparent 58%),
    linear-gradient(180deg, rgb(255 255 255 / 0.2), rgb(var(--auth-accent-rgb) / 0.08));
  filter: blur(0.4px);
}

.exposure-sweep {
  background: linear-gradient(94deg, transparent 0%, rgb(255 255 255 / 0.62) 44%, rgb(var(--auth-accent-rgb) / 0.18) 54%, transparent 74%);
  filter: blur(16px);
  mix-blend-mode: screen;
  transform: translate3d(-58%, 0, 0) scaleX(0.58);
}

.exposure-line {
  inset: 8% auto 8% 10%;
  width: 1px;
  border-radius: 999px;
  background: linear-gradient(180deg, transparent, rgb(255 255 255 / 0.92) 20%, rgb(var(--auth-accent-rgb) / 0.46) 58%, transparent);
  box-shadow:
    0 0 18px rgb(255 255 255 / 0.62),
    0 0 52px rgb(var(--auth-accent-rgb) / 0.22);
}

.auth-switch-host.is-developing .exposure-paper {
  animation: exposure-paper var(--develop-duration) var(--ease-out-soft) both;
}

.auth-switch-host.is-developing .exposure-sweep {
  animation: exposure-sweep var(--develop-duration) var(--ease-out-soft) both;
}

.auth-switch-host.is-developing .exposure-line {
  animation: exposure-line var(--develop-duration) cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.auth-switch-host.develop-to-login .exposure-sweep {
  animation-name: exposure-sweep-reverse;
}

.auth-switch-host.develop-to-login .exposure-line {
  animation-name: exposure-line-reverse;
}

/* 只覆盖嵌入式登录/注册面板的视觉样式，表单逻辑继续留在子组件中。 */
.auth-switch-host :deep(.auth-pane) {
  position: absolute;
  inset: 0;
  width: 100%;
  background: transparent !important;
  pointer-events: none;
}

.auth-switch-host :deep(.auth-pane.is-active) {
  position: relative;
  z-index: 3;
  pointer-events: auto;
}

.auth-switch-host :deep(.auth-pane.is-inactive) {
  z-index: 1;
}

.auth-switch-host :deep(.auth-page) {
  min-height: auto;
  display: block;
  grid-template-columns: 1fr;
  overflow: visible;
  background: transparent;
  animation: none !important;
}

.auth-switch-host :deep(.auth-panel) {
  min-height: auto;
  position: relative;
  z-index: 1;
  display: block;
  padding: 0;
  overflow: visible;
  background: transparent;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translate3d(0, 14px, 0) scale(0.992);
  filter: blur(8px) saturate(0.84);
  transition:
    opacity 220ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 380ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 340ms cubic-bezier(0.16, 1, 0.3, 1),
    visibility 0s linear 340ms;
}

.auth-switch-host :deep(.auth-panel::before),
.auth-switch-host :deep(.auth-panel::after) {
  content: none !important;
  display: none !important;
}

.auth-switch-host :deep(.auth-pane.is-active .auth-panel) {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translate3d(0, 0, 0) scale(1);
  filter: blur(0) saturate(1);
  transition:
    opacity 320ms 150ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 480ms 140ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 440ms 150ms cubic-bezier(0.16, 1, 0.3, 1);
}

.auth-switch-host :deep(.auth-pane.is-inactive .auth-panel) {
  transform: translate3d(0, -10px, 0) scale(1.004);
}

.auth-switch-host :deep(.auth-card) {
  box-sizing: border-box;
  position: relative;
  z-index: 1;
  width: 100%;
  min-height: auto;
  padding: clamp(30px, 3.2vw, 42px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  border: 1px solid rgb(226 232 222 / 0.96);
  border-radius: 28px;
  background:
    linear-gradient(180deg, var(--auth-card-bg), rgb(255 255 255 / 0.78)),
    radial-gradient(circle at 18% 0%, rgb(var(--auth-accent-rgb) / 0.07), transparent 16rem);
  box-shadow:
    0 32px 88px rgb(45 60 48 / 0.16),
    0 0 0 1px rgb(255 255 255 / 0.54),
    0 0 0 1px var(--auth-panel-shadow),
    inset 0 1px 0 rgb(255 255 255 / 0.72);
  backdrop-filter: blur(22px) saturate(1.08);
  transform-origin: center;
  animation: none !important;
  transition:
    transform 460ms var(--ease-out-soft),
    box-shadow 460ms var(--transition-slow),
    border-color 460ms var(--transition-slow),
    filter 460ms var(--transition-slow);
}

.auth-switch-host.is-register-mode :deep(.auth-card) {
  padding-block: clamp(24px, 2.5vw, 34px);
}

.auth-switch-host :deep(.auth-pane.is-active .auth-card) {
  transform: translate3d(0, 0, 0) scale(1);
  filter: saturate(1) contrast(1);
}

.auth-switch-host :deep(.auth-pane.is-inactive .auth-card) {
  transform: translate3d(0, 7px, 0) scale(0.992);
  filter: saturate(0.82) contrast(0.92);
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-card) {
  border-color: rgb(var(--auth-accent-rgb) / 0.24);
  transform: translate3d(0, 1px, 0) scale(0.998);
}

.auth-switch-host :deep(.auth-heading) {
  margin-bottom: 24px;
  text-align: left;
}

.auth-switch-host :deep(.auth-heading .eyebrow) {
  color: rgb(var(--auth-accent-rgb));
  font-size: 11px;
  letter-spacing: 0;
}

.auth-switch-host :deep(.auth-heading h2) {
  margin: 8px 0;
  color: var(--color-ink);
  font-size: 30px;
  line-height: 1.12;
  letter-spacing: 0;
}

.auth-switch-host :deep(.auth-heading p) {
  color: var(--color-muted);
  font-size: 14px;
}

.auth-switch-host :deep(.auth-tabs) {
  margin-bottom: 26px;
  padding: 5px;
  border: 1px solid rgb(216 222 212 / 0.94);
  border-radius: 999px;
  background: rgb(226 232 224 / 0.82);
}

.auth-switch-host :deep(.auth-tabs span),
.auth-switch-host :deep(.auth-tabs a) {
  min-height: 38px;
  border-radius: 999px;
  color: var(--color-muted);
  transition:
    color 220ms var(--ease-out-soft),
    background 220ms var(--ease-out-soft),
    box-shadow 220ms var(--ease-out-soft),
    transform 220ms var(--ease-out-soft);
}

.auth-switch-host :deep(.auth-tabs a:hover) {
  color: var(--color-ink);
  background: rgb(255 255 255 / 0.46);
  transform: translateY(-1px);
}

.auth-switch-host :deep(.auth-tabs .active) {
  color: var(--color-ink);
  background: rgb(255 255 255 / 0.96);
  box-shadow:
    0 8px 20px var(--auth-panel-shadow),
    inset 0 1px 0 rgb(255 255 255 / 0.82);
}

.auth-switch-host :deep(.auth-form) {
  gap: 16px;
}

.auth-switch-host :deep(.auth-form > label) {
  color: var(--color-muted);
  font-size: 13px;
}

.auth-switch-host :deep(.auth-input) {
  min-height: 50px;
  border: 1px solid rgb(210 216 207 / 0.92);
  border-radius: 16px;
  background: rgb(242 245 240 / 0.92);
  color: var(--color-ink);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.86),
    0 1px 0 rgb(255 255 255 / 0.44);
}

.auth-switch-host :deep(.auth-input::placeholder) {
  color: #a1a69f;
}

.auth-switch-host :deep(.auth-input:focus) {
  border-color: rgb(var(--auth-accent-rgb) / 0.5);
  background: #fff;
  box-shadow:
    inset 0 0 0 1px rgb(var(--auth-accent-rgb) / 0.24),
    0 0 0 5px rgb(var(--auth-accent-rgb) / 0.1),
    0 14px 34px rgb(var(--auth-accent-rgb) / 0.08);
  transform: translateY(-1px);
}

.auth-switch-host :deep(.input-error) {
  color: var(--color-red);
}

.auth-switch-host :deep(.form-row) {
  color: var(--color-muted);
}

.auth-switch-host :deep(.remember-check) {
  color: var(--color-muted);
}

.auth-switch-host :deep(.check-mark) {
  border-color: var(--color-line-strong);
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 6px 12px rgb(23 23 23 / 0.04);
}

.auth-switch-host :deep(.remember-check input:checked + .check-mark) {
  border-color: rgb(var(--auth-accent-rgb));
  background: rgb(var(--auth-accent-rgb));
  box-shadow: 0 8px 16px rgb(var(--auth-accent-rgb) / 0.22);
}

.auth-switch-host :deep(.text-button) {
  color: var(--color-muted);
}

.auth-switch-host :deep(.text-button:hover) {
  color: rgb(var(--auth-accent-rgb));
}

.auth-switch-host :deep(.btn-auth) {
  min-height: 52px;
  border: 1px solid rgb(23 23 23 / 0.86);
  border-radius: 16px;
  background: linear-gradient(180deg, #252525, #111);
  color: #fff;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.12),
    0 10px 24px rgb(23 23 23 / 0.12);
}

.auth-switch-host :deep(.btn-auth:hover:not(:disabled)) {
  transform: translateY(-1px);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.18),
    0 14px 34px rgb(23 23 23 / 0.16),
    0 0 0 5px rgb(var(--auth-accent-rgb) / 0.1);
}

.auth-switch-host :deep(.auth-divider) {
  margin: 30px 0 16px;
  color: var(--color-soft);
}

.auth-switch-host :deep(.auth-divider::before),
.auth-switch-host :deep(.auth-divider::after) {
  background: var(--color-line);
}

.auth-switch-host :deep(.social-row) {
  gap: 12px;
}

.auth-switch-host :deep(.social-row button) {
  min-height: 48px;
  border: 1px solid rgb(218 224 215 / 0.94);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.88);
  color: var(--color-ink);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.8);
}

.auth-switch-host :deep(.social-row button:hover) {
  border-color: rgb(var(--auth-accent-rgb) / 0.24);
  background: #fff;
  box-shadow:
    0 14px 28px rgb(23 23 23 / 0.08);
}

.auth-switch-host :deep(.auth-note) {
  color: var(--color-muted);
}

.auth-switch-host :deep(.auth-heading),
.auth-switch-host :deep(.auth-tabs),
.auth-switch-host :deep(.field-line),
.auth-switch-host :deep(.form-row),
.auth-switch-host :deep(.btn-auth),
.auth-switch-host :deep(.auth-divider),
.auth-switch-host :deep(.social-row),
.auth-switch-host :deep(.auth-note) {
  letter-spacing: 0;
  transition:
    opacity 300ms var(--ease-out-soft),
    transform 380ms var(--ease-out-soft),
    filter 320ms var(--ease-out-soft);
}

.auth-switch-host :deep(.auth-pane.is-active .auth-heading),
.auth-switch-host :deep(.auth-pane.is-active .auth-tabs),
.auth-switch-host :deep(.auth-pane.is-active .field-line),
.auth-switch-host :deep(.auth-pane.is-active .form-row),
.auth-switch-host :deep(.auth-pane.is-active .btn-auth),
.auth-switch-host :deep(.auth-pane.is-active .auth-divider),
.auth-switch-host :deep(.auth-pane.is-active .social-row),
.auth-switch-host :deep(.auth-pane.is-active .auth-note) {
  opacity: 1;
  transform: translate3d(0, 0, 0);
  filter: blur(0);
}

.auth-switch-host :deep(.auth-pane.is-inactive .auth-heading),
.auth-switch-host :deep(.auth-pane.is-inactive .auth-tabs),
.auth-switch-host :deep(.auth-pane.is-inactive .field-line),
.auth-switch-host :deep(.auth-pane.is-inactive .form-row),
.auth-switch-host :deep(.auth-pane.is-inactive .btn-auth),
.auth-switch-host :deep(.auth-pane.is-inactive .auth-divider),
.auth-switch-host :deep(.auth-pane.is-inactive .social-row),
.auth-switch-host :deep(.auth-pane.is-inactive .auth-note) {
  opacity: 0;
  transform: translate3d(0, 10px, 0);
  filter: blur(5px);
}

.auth-switch-host :deep(.auth-pane.is-active .field-line:nth-of-type(1)) {
  transition-delay: 24ms;
}

.auth-switch-host :deep(.auth-pane.is-active .field-line:nth-of-type(2)) {
  transition-delay: 48ms;
}

.auth-switch-host :deep(.auth-pane.is-active .field-line:nth-of-type(3)) {
  transition-delay: 72ms;
}

.auth-switch-host :deep(.auth-pane.is-active .form-row),
.auth-switch-host :deep(.auth-pane.is-active .btn-auth),
.auth-switch-host :deep(.auth-pane.is-active .auth-note) {
  transition-delay: 96ms;
}

.auth-switch-host :deep(.auth-pane.is-active .auth-divider),
.auth-switch-host :deep(.auth-pane.is-active .social-row) {
  transition-delay: 120ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-heading) {
  transition-delay: 180ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-tabs) {
  transition-delay: 215ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .field-line:nth-of-type(1)) {
  transition-delay: 250ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .field-line:nth-of-type(2)) {
  transition-delay: 285ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .field-line:nth-of-type(3)) {
  transition-delay: 320ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .form-row),
.auth-switch-host.is-developing :deep(.auth-pane.is-active .btn-auth),
.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-note) {
  transition-delay: 355ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-divider),
.auth-switch-host.is-developing :deep(.auth-pane.is-active .social-row) {
  transition-delay: 390ms;
}

.auth-switch-host :deep(.auth-page),
.auth-switch-host :deep(.auth-panel),
.auth-switch-host :deep(.auth-card),
.auth-switch-host :deep(.auth-heading),
.auth-switch-host :deep(.auth-tabs),
.auth-switch-host :deep(.auth-tabs::before),
.auth-switch-host :deep(.field-line),
.auth-switch-host :deep(.form-row),
.auth-switch-host :deep(.btn-auth),
.auth-switch-host :deep(.auth-divider),
.auth-switch-host :deep(.social-row),
.auth-switch-host :deep(.auth-note) {
  animation: none !important;
}

@keyframes exposure-layer {
  0%, 100% {
    opacity: 0;
  }

  12%, 74% {
    opacity: 1;
  }
}

@keyframes exposure-paper {
  0%, 100% {
    opacity: 0;
  }

  20% {
    opacity: 0.46;
  }

  62% {
    opacity: 0.28;
  }
}

@keyframes exposure-sweep {
  0% {
    opacity: 0;
    transform: translate3d(-58%, 0, 0) scaleX(0.58);
  }

  24% {
    opacity: 0.78;
  }

  68% {
    opacity: 0.44;
    transform: translate3d(22%, 0, 0) scaleX(1.04);
  }

  100% {
    opacity: 0;
    transform: translate3d(66%, 0, 0) scaleX(0.66);
  }
}

@keyframes exposure-sweep-reverse {
  0% {
    opacity: 0;
    transform: translate3d(66%, 0, 0) scaleX(0.66);
  }

  24% {
    opacity: 0.78;
  }

  68% {
    opacity: 0.44;
    transform: translate3d(-22%, 0, 0) scaleX(1.04);
  }

  100% {
    opacity: 0;
    transform: translate3d(-58%, 0, 0) scaleX(0.58);
  }
}

@keyframes exposure-line {
  0% {
    left: 12%;
    opacity: 0;
  }

  20% {
    opacity: 0.76;
  }

  72% {
    left: 84%;
    opacity: 0.4;
  }

  100% {
    left: 92%;
    opacity: 0;
  }
}

@keyframes exposure-line-reverse {
  0% {
    left: 88%;
    opacity: 0;
  }

  20% {
    opacity: 0.76;
  }

  72% {
    left: 16%;
    opacity: 0.4;
  }

  100% {
    left: 8%;
    opacity: 0;
  }
}

@media (max-width: 900px) {
  .auth-switch-host {
    align-items: start;
    --grid-size: 50px;
    --grid-softness: 144px;
    padding: 56px 18px 28px;
  }

  .auth-shell {
    width: min(100%, 520px);
    grid-template-columns: 1fr;
    gap: 32px;
  }

  .auth-intro {
    justify-items: center;
    text-align: center;
  }

  .intro-mark {
    width: 50px;
    height: 50px;
    margin-bottom: 18px;
  }

  .auth-intro h1 {
    font-size: clamp(52px, 17vw, 76px);
  }

  .auth-intro p {
    max-width: 430px;
    margin-top: 18px;
    font-size: 14px;
  }

  .intro-badges {
    justify-content: center;
    margin-top: 20px;
  }

}

@media (max-width: 520px) {
  .auth-switch-host {
    --grid-size: 42px;
    --grid-softness: 124px;
    padding: 42px 12px 20px;
  }

  .auth-shell {
    gap: 24px;
  }

  .auth-intro p,
  .intro-badges {
    display: none;
  }

  .auth-switch-host :deep(.auth-card) {
    padding: 22px 18px;
    border-radius: 16px;
  }

  .auth-switch-host :deep(.social-row) {
    grid-template-columns: 1fr;
  }

  .auth-exposure-layer {
    inset: -8px;
    border-radius: 20px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth-canvas-primary,
  .auth-exposure-layer,
  .auth-exposure-layer span,
  .auth-switch-host :deep(.auth-panel),
  .auth-switch-host :deep(.auth-pane.is-active .auth-panel),
  .auth-switch-host :deep(.auth-pane.is-inactive .auth-panel),
  .auth-switch-host :deep(.auth-card),
  .auth-switch-host :deep(.auth-heading),
  .auth-switch-host :deep(.auth-tabs),
  .auth-switch-host :deep(.field-line),
  .auth-switch-host :deep(.form-row),
  .auth-switch-host :deep(.btn-auth),
  .auth-switch-host :deep(.auth-divider),
  .auth-switch-host :deep(.social-row),
  .auth-switch-host :deep(.auth-note) {
    animation: none !important;
    transition: none;
  }

  .auth-switch-host :deep(.auth-panel),
  .auth-switch-host :deep(.auth-card) {
    transform: none;
    filter: none;
  }
}
</style>
