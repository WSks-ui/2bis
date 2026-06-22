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
    @click.capture="handleAuthSwitchIntent"
  >
    <div class="auth-canvas" aria-hidden="true">
      <Transition name="auth-preview-fade">
        <img
          v-if="activeScene.preview"
          :key="`preview-${activeScene.preview}`"
          class="auth-canvas-image auth-canvas-preview"
          :src="activeScene.preview"
          alt=""
          decoding="async"
        />
      </Transition>
      <Transition name="auth-scene-fade">
        <img
          :key="activeScene.image"
          class="auth-canvas-image auth-canvas-primary"
          :src="activeScene.image"
          alt=""
          decoding="async"
          fetchpriority="high"
        />
      </Transition>
      <!-- 背景可读性蒙版：统一一层，保证不同明暗新图接入时文字对比度稳定 -->
      <div class="auth-canvas-veil"></div>
      <!-- 远景网格层：位移小、更稳，营造纵深 -->
      <div class="auth-canvas-grid auth-canvas-grid--far"></div>
      <!-- 主网格层：常驻安静，交互时局部高亮/拖拽/尾迹 -->
      <div class="auth-canvas-grid auth-canvas-grid--main"></div>
      <div class="auth-canvas-vignette"></div>
      <div class="auth-canvas-grain"></div>
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

      <section class="auth-workbench" aria-label="账户入口" :aria-busy="String(isDeveloping)">
        <div class="workbench-shadow" aria-hidden="true"></div>
        <div class="auth-exposure-layer" aria-hidden="true">
          <span class="exposure-paper"></span>
          <span class="exposure-sweep"></span>
          <span class="exposure-line"></span>
          <span class="exposure-grain"></span>
        </div>

        <Login
          class="auth-pane"
          :show-showcase="false"
          :class="{ 'is-active': isLogin, 'is-inactive': !isLogin }"
          :aria-hidden="String(!isLogin)"
          :inert="!isLogin || undefined"
        />
        <Register
          class="auth-pane"
          :show-showcase="false"
          :class="{ 'is-active': isRegister, 'is-inactive': !isRegister }"
          :aria-hidden="String(!isRegister)"
          :inert="!isRegister || undefined"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { useAuthGridInteraction } from '../composables/useAuthGridInteraction'
import { AUTH_FALLBACK_SCENES, getAuthShowcaseScenes, preloadAuthImages } from '../utils/authAssets'
import Login from './Login.vue'
import Register from './Register.vue'

defineOptions({ name: 'AuthView' })

const route = useRoute()
const router = useRouter()
const isRegister = computed(() => route.name === 'Register')
const isLogin = computed(() => !isRegister.value)
const authRouteNames = new Set(['Login', 'Register'])
// 显影时长略加，让分层显影动作可被感知但不拖沓（仍 ≤1s）。
const DEVELOP_TRANSITION_MS = 920
// 先让曝光层与旧表单响应，再推进路由；避免 SPA 同帧换页吞掉显影起点。
const DEVELOP_ROUTE_DELAY_MS = 180
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
let routeSwitchTimer = 0
let sceneTimer = 0

watch(
  () => route.name,
  (nextName, previousName) => {
    if (!authRouteNames.has(nextName) || !authRouteNames.has(previousName) || nextName === previousName) return

    prepareDevelopTransition(nextName)
  },
  { flush: 'sync' }
)

onBeforeRouteUpdate((to, from) => {
  if (!authRouteNames.has(to.name) || !authRouteNames.has(from.name) || to.name === from.name) return

  // 组件被 KeepAlive 复用时，路由更新守卫比 DOM 更新更早，适合作为显影动画的稳定入口。
  prepareDevelopTransition(to.name)
})

onMounted(loadAuthScenes)
onBeforeUnmount(() => {
  clearDevelopTimer()
  clearRouteSwitchTimer()
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

function prepareDevelopTransition(nextName) {
  developDirection.value = nextName === 'Register' ? 'to-register' : 'to-login'
  startDevelopTransition()
}

function startDevelopTransition() {
  // 暗房显影：多层显影序列——纸面渐显、曝光带扫过、扫描线带残影、颗粒质感，全程冷白。
  clearDevelopTimer()
  isDeveloping.value = true
  developTimer = window.setTimeout(() => {
    isDeveloping.value = false
    developTimer = 0
  }, DEVELOP_TRANSITION_MS)
}

function handleAuthSwitchIntent(event) {
  const link = event.target?.closest?.('a[href="/login"], a[href="/register"]')
  if (!link) return
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return

  const nextName = link.getAttribute('href') === '/register' ? 'Register' : 'Login'
  if (nextName === route.name || !authRouteNames.has(route.name)) return

  event.preventDefault()
  event.stopPropagation()

  // 认证页内部切换由壳层统一接管：先显影，再短延迟换路由，保证动画起点稳定可见。
  prepareDevelopTransition(nextName)
  clearRouteSwitchTimer()
  routeSwitchTimer = window.setTimeout(() => {
    routeSwitchTimer = 0
    router.push(link.getAttribute('href'))
  }, DEVELOP_ROUTE_DELAY_MS)
}

function clearDevelopTimer() {
  if (!developTimer) return
  window.clearTimeout(developTimer)
  developTimer = 0
}

function clearRouteSwitchTimer() {
  if (!routeSwitchTimer) return
  window.clearTimeout(routeSwitchTimer)
  routeSwitchTimer = 0
}

function clearSceneTimer() {
  if (!sceneTimer) return
  window.clearInterval(sceneTimer)
  sceneTimer = 0
}
</script>

<style scoped>
/* ============================================================
   Auth 设计 Token —— 卡片/网格/显影/换图共用一组变量
   ============================================================ */
.auth-switch-host {
  position: relative;
  box-sizing: border-box;
  min-height: 100vh;
  min-height: 100svh;
  /* 强调色与语义色 */
  --auth-accent-rgb: 72 147 90;
  --auth-success-rgb: 72 147 90;
  --auth-page-ink: #182219;
  --auth-page-muted: rgb(48 61 52 / 0.8);
  /* 卡片与控件底色 */
  --auth-card-bg: rgb(255 255 255 / 0.94);
  --auth-control-bg: hsl(134deg 10% 95%);
  --auth-control-bg-strong: hsl(134deg 9% 92%);
  --auth-panel-line: rgb(34 61 43 / 0.32);
  --auth-panel-shadow: rgb(72 147 90 / 0.14);
  /* 显影时长与缓动：登录↔注册共享，确保镜像一致 */
  --develop-duration: 920ms;
  --develop-ease: cubic-bezier(0.22, 0.78, 0.2, 1);
  /* 背景可读性蒙版强度 */
  --auth-canvas-veil: 0.28;
  --auth-workbench-shift: clamp(0px, 7vw, 92px);
  /* 网格交互变量（由 useAuthGridInteraction 动态写入） */
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
  /* 景深分层变量（由 useAuthGridInteraction 动态写入） */
  --grid-depth-near-x: 0px;
  --grid-depth-near-y: 0px;
  --grid-depth-far-x: 0px;
  --grid-depth-far-y: 0px;
  --grid-parallax-tilt-x: 0deg;
  --grid-parallax-tilt-y: 0deg;
  --grid-depth-intensity: 0;
  display: grid;
  place-items: center;
  overflow-x: hidden;
  overflow-y: auto;
  padding: clamp(24px, 4.5vw, 64px) 20px;
  background: linear-gradient(135deg, #f8faf5 0%, #eef5f1 48%, #f2f5f9 100%);
  color: var(--auth-page-ink);
}

/* ============================================================
   背景画布层
   ============================================================ */
.auth-canvas,
.auth-canvas::before,
.auth-canvas::after,
.auth-canvas-image,
.auth-canvas-veil,
.auth-canvas-grid,
.auth-canvas-vignette,
.auth-canvas-grain {
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
  opacity: 0.06;
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
  transform: scale(1.035);
  filter: saturate(1.06) contrast(1.04) brightness(0.93);
  opacity: 0.96;
}

/* 多图轮换：preview 先柔和过渡，primary 再完成清晰显影，未来新增图片时不突兀。 */
.auth-preview-fade-enter-active,
.auth-preview-fade-leave-active {
  transition:
    opacity 900ms var(--ease-out-soft, ease-out),
    filter 900ms var(--ease-out-soft, ease-out),
    transform 1200ms var(--ease-out-soft, ease-out);
}

.auth-preview-fade-enter-from,
.auth-preview-fade-leave-to {
  opacity: 0;
  filter: blur(38px) saturate(0.84) brightness(1);
  transform: scale(1.12);
}

.auth-scene-fade-enter-active,
.auth-scene-fade-leave-active {
  transition:
    opacity 1100ms var(--ease-out-soft, ease-out),
    filter 1100ms var(--ease-out-soft, ease-out),
    transform 1300ms var(--ease-out-soft, ease-out);
}

.auth-scene-fade-enter-from {
  opacity: 0;
  filter: saturate(0.92) contrast(0.96) brightness(1.02) blur(6px);
  transform: scale(1.065);
}

.auth-scene-fade-leave-to {
  opacity: 0;
  filter: saturate(0.94) contrast(0.98) brightness(0.98) blur(8px);
  transform: scale(1.02);
}

/* 可读性蒙版：统一一层浅色覆盖，保证不同明暗新图文字对比度稳定、不过度泛白 */
.auth-canvas-veil {
  z-index: 3;
  background:
    radial-gradient(ellipse at 58% 48%, rgb(255 255 255 / 0.08), transparent 32rem),
    linear-gradient(135deg,
      rgb(248 250 245 / calc(var(--auth-canvas-veil) + 0.06)) 0%,
      rgb(244 248 242 / var(--auth-canvas-veil)) 52%,
      rgb(242 246 248 / calc(var(--auth-canvas-veil) - 0.06)) 100%);
}
/* ============================================================
   背景网格 —— 景深分层：远景 + 主层
   ============================================================ */

/* 共用网格背景定义 mixin（通过重复属性实现，因为 scoped 无预处理器） */
.auth-canvas-grid {
  overflow: hidden;
  background-image:
    linear-gradient(rgb(20 39 25 / 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgb(20 39 25 / 0.1) 1px, transparent 1px),
    linear-gradient(rgb(247 255 249 / 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgb(247 255 249 / 0.08) 1px, transparent 1px);
  background-position: 50% 50%, 50% 50%, 0 0, 0 0;
  background-size:
    var(--grid-size) var(--grid-size),
    var(--grid-size) var(--grid-size),
    calc(var(--grid-size) * 0.5) calc(var(--grid-size) * 0.5),
    calc(var(--grid-size) * 0.5) calc(var(--grid-size) * 0.5);
  mix-blend-mode: normal;
}

/* 远景网格层：更淡、更小、位移更小，营造纵深 */
.auth-canvas-grid--far {
  z-index: 6;
  opacity: 0.22;
  background-size:
    calc(var(--grid-size) * 0.72) calc(var(--grid-size) * 0.72),
    calc(var(--grid-size) * 0.72) calc(var(--grid-size) * 0.72),
    calc(var(--grid-size) * 0.36) calc(var(--grid-size) * 0.36),
    calc(var(--grid-size) * 0.36) calc(var(--grid-size) * 0.36);
  transform:
    translate3d(var(--grid-depth-far-x), var(--grid-depth-far-y), 0)
    rotate3d(1, 0, 0, var(--grid-parallax-tilt-y))
    rotate3d(0, 1, 0, var(--grid-parallax-tilt-x));
  transition: transform 120ms linear;
  will-change: transform;
  filter: blur(0.4px);
}

/* 主网格层：常驻安静，交互时局部高亮/拖拽/尾迹 */
.auth-canvas-grid--main {
  z-index: 8;
  opacity: 0.4;
  transform:
    translate3d(var(--grid-depth-near-x), var(--grid-depth-near-y), 0)
    rotate3d(1, 0, 0, calc(var(--grid-parallax-tilt-y) * 1.6))
    rotate3d(0, 1, 0, calc(var(--grid-parallax-tilt-x) * 1.6));
  transition: transform 80ms linear;
  will-change: transform;
}

.auth-canvas-grid--main::before,
.auth-canvas-grid--main::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

/* 交互高亮层：随指针游走的局部高亮网格，带拖拽形变 */
.auth-canvas-grid--main::before {
  z-index: 1;
  background-image:
    linear-gradient(90deg, rgb(33 66 43 / 0.42) 1px, transparent 1px),
    linear-gradient(180deg, rgb(33 66 43 / 0.38) 1px, transparent 1px),
    linear-gradient(90deg, rgb(246 255 248 / 0.3) 1px, transparent 1px),
    linear-gradient(180deg, rgb(246 255 248 / 0.24) 1px, transparent 1px);
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
  opacity: 0.28;
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
  transition: opacity 180ms var(--ease-out-soft, ease-out);
  will-change: transform, opacity, background-position;
}

/* 交互光晕层：跟随指针的柔和径向光，增强空间感 */
.auth-canvas-grid--main::after {
  z-index: 2;
  opacity: 0.24;
  background:
    radial-gradient(ellipse at var(--grid-target-x) var(--grid-target-y), rgb(248 255 250 / 0.22), transparent 18rem),
    radial-gradient(ellipse at var(--grid-x) var(--grid-y), rgb(var(--auth-accent-rgb) / 0.14), transparent 13rem),
    radial-gradient(ellipse at var(--grid-tail-x) var(--grid-tail-y), rgb(22 54 35 / 0.1), transparent 10rem);
  mix-blend-mode: screen;
  transition: opacity 180ms var(--ease-out-soft, ease-out);
}

/* 交互激活时：高亮与光晕增强，景深层位移更明显 */
.auth-switch-host.is-grid-active .auth-canvas-grid--main {
  opacity: 0.5;
}

.auth-switch-host.is-grid-active .auth-canvas-grid--main::before {
  opacity: 0.72;
}

.auth-switch-host.is-grid-active .auth-canvas-grid--main::after {
  opacity: 0.6;
}

.auth-switch-host.is-grid-active .auth-canvas-grid--far {
  opacity: 0.3;
}

/* 暗角与颗粒层 */
.auth-canvas-vignette {
  z-index: 4;
  background:
    radial-gradient(ellipse at 54% 48%, transparent 0 46%, rgb(255 255 255 / 0.03) 76%, rgb(226 235 229 / 0.18) 100%),
    linear-gradient(90deg, rgb(244 248 242 / 0.2) 0%, transparent 34%, rgb(244 248 242 / 0.08) 100%);
}

/* 常驻极轻颗粒：让背景有胶片质感，不喧宾夺主 */
.auth-canvas-grain {
  z-index: 9;
  opacity: 0.04;
  background-image:
    radial-gradient(circle, rgb(30 47 36 / 0.4) 0 0.5px, transparent 0.6px);
  background-size: 3px 3px;
  mix-blend-mode: multiply;
}
/* ============================================================
   左侧 intro 排版
   ============================================================ */
.auth-shell {
  position: relative;
  z-index: 10;
  width: min(100%, 1180px);
  min-height: min(760px, calc(100svh - clamp(48px, 9vw, 128px)));
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas: 'stage';
  place-items: center;
  align-items: center;
}

.auth-intro {
  min-width: 0;
  position: absolute;
  top: clamp(0px, 2vw, 24px);
  left: clamp(0px, 1.5vw, 18px);
  z-index: 1;
  display: grid;
  justify-items: start;
  max-width: 390px;
  color: var(--auth-page-ink);
  isolation: isolate;
}

.auth-intro::before {
  content: '';
  position: absolute;
  inset: -24px -34px -28px -24px;
  z-index: -1;
  border-radius: 24px;
  background: radial-gradient(ellipse at 20% 42%, rgb(255 255 255 / 0.26), rgb(255 255 255 / 0.08) 58%, transparent 78%);
  filter: blur(10px);
}

.intro-mark {
  width: 46px;
  height: 46px;
  margin-bottom: 20px;
  display: grid;
  place-items: center;
  border: 1px solid rgb(var(--auth-accent-rgb) / 0.26);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgb(255 255 255 / 0.94), rgb(246 249 244 / 0.76)),
    radial-gradient(circle at 50% 35%, rgb(var(--auth-accent-rgb) / 0.18), transparent 72%);
  box-shadow:
    0 18px 46px rgb(45 68 52 / 0.16),
    inset 0 1px 0 rgb(255 255 255 / 0.72);
}

.intro-mark-core {
  position: relative;
  width: 18px;
  height: 18px;
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
  height: 18px;
  box-shadow:
    8px 0 0 rgb(var(--auth-accent-rgb) / 0.22),
    -8px 0 0 rgb(var(--auth-accent-rgb) / 0.22);
}

.intro-mark-core::after {
  width: 18px;
  height: 3px;
  box-shadow:
    0 8px 0 rgb(var(--auth-accent-rgb) / 0.22),
    0 -8px 0 rgb(var(--auth-accent-rgb) / 0.22);
}

.intro-kicker {
  margin-bottom: 10px;
  color: rgb(var(--auth-accent-rgb) / 0.9);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 820;
  letter-spacing: 0;
}

.auth-intro h1 {
  margin: 0;
  color: #1b241d;
  font-family: var(--font-heading);
  font-size: clamp(56px, 7vw, 88px);
  font-style: italic;
  font-weight: 950;
  line-height: 0.9;
  letter-spacing: 0;
  /* 单层柔和投影，替换旧版多层重投影，避免浅色背景上发灰发糊 */
  text-shadow: 0 12px 34px rgb(255 255 255 / 0.72);
}

.auth-intro p {
  max-width: 360px;
  margin: 18px 0 0;
  color: var(--auth-page-muted);
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 580;
  line-height: 1.75;
}

.intro-badges {
  margin-top: 22px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.intro-badges span {
  min-height: 32px;
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
  font-weight: 680;
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
/* ============================================================
   右侧表单 workbench + 显影层
   ============================================================ */
.auth-workbench {
  position: relative;
  z-index: 2;
  width: min(100%, 444px);
  grid-area: stage;
  justify-self: center;
  transform: translate3d(var(--auth-workbench-shift), 0, 0);
  isolation: isolate;
}

.workbench-shadow {
  position: absolute;
  inset: 6% -10% -12%;
  z-index: -1;
  border-radius: 28px;
  background:
    radial-gradient(ellipse at 50% 0%, rgb(255 255 255 / 0.64), transparent 56%),
    radial-gradient(ellipse at 50% 58%, rgb(var(--auth-accent-rgb) / 0.12), transparent 68%),
    radial-gradient(ellipse at 50% 100%, rgb(30 47 36 / 0.08), transparent 62%);
  filter: blur(30px);
}

/* 显影层：覆盖在卡片上方的多层显影动作容器 */
.auth-exposure-layer {
  position: absolute;
  inset: -14px;
  z-index: 12;
  overflow: hidden;
  border-radius: 30px;
  opacity: 0;
  pointer-events: none;
}

.auth-switch-host.is-developing .auth-exposure-layer {
  animation: exposure-layer var(--develop-duration) var(--develop-ease) both;
}

.auth-exposure-layer span {
  position: absolute;
  inset: 0;
  opacity: 0;
}

/* 底层显影纸：渐显的冷白纸面 */
.exposure-paper {
  background:
    radial-gradient(ellipse at 50% 42%, rgb(255 255 255 / 0.36), transparent 58%),
    linear-gradient(180deg, rgb(255 255 255 / 0.22), rgb(var(--auth-accent-rgb) / 0.06));
  filter: blur(0.4px);
}

/* 曝光带：真正会扫过卡片的光带，方向感、峰值、尾光衰减分明 */
.exposure-sweep {
  background: linear-gradient(94deg,
    transparent 0%,
    rgb(255 255 255 / 0.72) 38%,
    rgb(255 255 255 / 0.88) 50%,
    rgb(var(--auth-accent-rgb) / 0.16) 62%,
    transparent 78%);
  filter: blur(14px);
  mix-blend-mode: screen;
  transform: translate3d(-62%, 0, 0) scaleX(0.5);
}

/* 扫描线：竖直细线带辉光，随曝光方向移动 */
.exposure-line {
  inset: 6% auto 6% 10%;
  width: 1px;
  border-radius: 999px;
  background: linear-gradient(180deg, transparent, rgb(255 255 255 / 0.94) 18%, rgb(var(--auth-accent-rgb) / 0.5) 58%, transparent);
  box-shadow:
    0 0 20px rgb(255 255 255 / 0.68),
    0 0 56px rgb(var(--auth-accent-rgb) / 0.24);
}

/* 显影颗粒：仅在显影期出现的胶片质感叠加，不残留 */
.exposure-grain {
  background-image:
    radial-gradient(circle, rgb(255 255 255 / 0.5) 0 0.5px, transparent 0.6px),
    radial-gradient(circle, rgb(30 47 36 / 0.3) 0 0.4px, transparent 0.5px);
  background-size: 3px 3px, 4px 4px;
  background-position: 0 0, 1px 2px;
  mix-blend-mode: overlay;
  filter: blur(0.3px);
}

.auth-switch-host.is-developing .exposure-paper {
  animation: exposure-paper var(--develop-duration) var(--develop-ease) both;
}

.auth-switch-host.is-developing .exposure-sweep {
  animation: exposure-sweep var(--develop-duration) var(--develop-ease) both;
}

.auth-switch-host.is-developing .exposure-line {
  animation: exposure-line var(--develop-duration) cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.auth-switch-host.is-developing .exposure-grain {
  animation: exposure-grain var(--develop-duration) steps(8) both;
}

/* 登录→注册 与 注册→登录 严格镜像 */
.auth-switch-host.develop-to-login .exposure-sweep {
  animation-name: exposure-sweep-reverse;
}

.auth-switch-host.develop-to-login .exposure-line {
  animation-name: exposure-line-reverse;
}
/* ============================================================
   内嵌面板与卡片样式覆盖（表单逻辑留在子组件中）
   ============================================================ */

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

/* 退影：旧面板轻微失焦+下沉+降饱和消散 */
.auth-switch-host :deep(.auth-pane.is-inactive .auth-panel) {
  transform: translate3d(0, -10px, 0) scale(1.004);
  filter: blur(6px) saturate(0.78) brightness(0.96);
}

.auth-switch-host :deep(.auth-card) {
  box-sizing: border-box;
  position: relative;
  z-index: 1;
  width: 100%;
  min-height: auto;
  padding: clamp(30px, 3vw, 40px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  border: 1px solid rgb(229 234 225 / 0.92);
  border-radius: 26px;
  background:
    linear-gradient(180deg, var(--auth-card-bg), rgb(255 255 255 / 0.88)),
    radial-gradient(circle at 16% 0%, rgb(var(--auth-accent-rgb) / 0.075), transparent 15rem);
  /* 收敛为 2 层结构光影，去掉发白溢光 */
  box-shadow:
    0 26px 70px rgb(45 60 48 / 0.16),
    0 0 0 1px rgb(255 255 255 / 0.48),
    inset 0 1px 0 rgb(255 255 255 / 0.72);
  backdrop-filter: blur(30px) saturate(1.06);
  transform-origin: center;
  animation: none !important;
  transition:
    transform 460ms var(--ease-out-soft, ease-out),
    box-shadow 460ms var(--transition-slow, ease),
    border-color 460ms var(--transition-slow, ease),
    filter 460ms var(--transition-slow, ease);
}

.auth-switch-host.is-register-mode :deep(.auth-card) {
  padding-block: clamp(24px, 2.35vw, 32px);
}

.auth-switch-host :deep(.auth-pane.is-active .auth-card) {
  transform: translate3d(0, 0, 0) scale(1);
  filter: saturate(1) contrast(1);
}

.auth-switch-host :deep(.auth-pane.is-inactive .auth-card) {
  transform: translate3d(0, 7px, 0) scale(0.992);
  filter: saturate(0.82) contrast(0.92);
}

/* 显影期：卡片在末段定影入位 */
.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-card) {
  border-color: rgb(var(--auth-accent-rgb) / 0.24);
  transform: translate3d(0, 1px, 0) scale(0.998);
  box-shadow:
    0 24px 66px rgb(45 60 48 / 0.14),
    0 0 0 1px rgb(255 255 255 / 0.5),
    inset 0 1px 0 rgb(255 255 255 / 0.78);
}
/* ============================================================
   控件质感统一：heading / tabs / input / button / social
   ============================================================ */
.auth-switch-host :deep(.auth-heading) {
  margin-bottom: 20px;
  text-align: left;
}

.auth-switch-host :deep(.auth-heading .eyebrow) {
  color: rgb(var(--auth-accent-rgb));
  font-size: 11px;
  font-weight: 820;
  letter-spacing: 0;
  text-transform: uppercase;
}

.auth-switch-host :deep(.auth-heading h2) {
  margin: 7px 0 8px;
  color: var(--color-ink);
  font-size: 29px;
  line-height: 1.12;
  letter-spacing: 0;
}

.auth-switch-host :deep(.auth-heading p) {
  color: var(--color-muted);
  font-size: 14px;
  line-height: 1.62;
}

.auth-switch-host :deep(.auth-tabs) {
  position: relative;
  margin-bottom: 22px;
  padding: 5px;
  border: 1px solid rgb(216 222 212 / 0.9);
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgb(232 237 229 / 0.88), rgb(224 230 222 / 0.82));
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.58),
    0 1px 0 rgb(255 255 255 / 0.4);
}

.auth-switch-host :deep(.auth-tabs span),
.auth-switch-host :deep(.auth-tabs a) {
  min-height: 38px;
  border-radius: 999px;
  color: var(--color-muted);
  outline: none;
  transition:
    color 220ms var(--ease-out-soft, ease-out),
    background 220ms var(--ease-out-soft, ease-out),
    box-shadow 220ms var(--ease-out-soft, ease-out),
    transform 220ms var(--ease-out-soft, ease-out);
}

.auth-switch-host :deep(.auth-tabs a:hover) {
  color: var(--color-ink);
  background: rgb(255 255 255 / 0.5);
  transform: none;
}

.auth-switch-host :deep(.auth-tabs a:focus-visible) {
  color: var(--color-ink);
  background: rgb(255 255 255 / 0.72);
  box-shadow:
    inset 0 0 0 1px rgb(var(--auth-accent-rgb) / 0.32),
    0 0 0 4px rgb(var(--auth-accent-rgb) / 0.12);
}

.auth-switch-host :deep(.auth-tabs .active) {
  color: var(--color-ink);
  background: rgb(255 255 255 / 0.96);
  box-shadow:
    0 8px 18px var(--auth-panel-shadow),
    inset 0 1px 0 rgb(255 255 255 / 0.82);
}

.auth-switch-host.is-developing :deep(.auth-tabs a) {
  pointer-events: none;
}

.auth-switch-host :deep(.auth-form) {
  gap: 15px;
}

.auth-switch-host :deep(.auth-form > label) {
  color: var(--color-muted);
  font-size: 13px;
}

.auth-switch-host :deep(.auth-input) {
  min-height: 50px;
  border: 1px solid rgb(208 216 207 / 0.92);
  border-radius: 15px;
  background: rgb(246 248 245 / 0.96);
  color: var(--color-ink);
  outline: none;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.86);
  transition:
    border-color 220ms var(--ease-out-soft, ease-out),
    background 220ms var(--ease-out-soft, ease-out),
    box-shadow 220ms var(--ease-out-soft, ease-out),
    transform 220ms var(--ease-out-soft, ease-out);
}

.auth-switch-host :deep(.auth-input::placeholder) {
  color: #a1a69f;
}

/* 字段获焦/失焦：细腻质感反馈——边框定影 + 柔光，去掉抖动位移 */
.auth-switch-host :deep(.auth-input:focus) {
  border-color: rgb(var(--auth-accent-rgb) / 0.5);
  background: #fff;
  box-shadow:
    inset 0 0 0 1px rgb(var(--auth-accent-rgb) / 0.24),
    0 0 0 5px rgb(var(--auth-accent-rgb) / 0.1);
  transform: none;
}

.auth-switch-host :deep(.auth-input[aria-invalid='true']) {
  border-color: rgb(183 66 66 / 0.52);
  background: rgb(255 250 249 / 0.98);
  box-shadow:
    inset 0 0 0 1px rgb(183 66 66 / 0.18),
    0 0 0 4px rgb(183 66 66 / 0.08);
}

.auth-switch-host :deep(.input-error) {
  min-height: 16px;
  color: var(--color-red);
  font-size: 12px;
  line-height: 1.32;
  opacity: 0;
  transition:
    opacity 180ms var(--ease-out-soft, ease-out);
}

.auth-switch-host :deep(.input-error.is-visible) {
  opacity: 1;
}

.auth-switch-host :deep(.form-row) {
  color: var(--color-muted);
}

.auth-switch-host :deep(.remember-check) {
  color: var(--color-muted);
}

.auth-switch-host :deep(.remember-check:focus-within .check-mark) {
  border-color: rgb(var(--auth-accent-rgb) / 0.58);
  box-shadow:
    0 8px 16px rgb(var(--auth-accent-rgb) / 0.12),
    0 0 0 4px rgb(var(--auth-accent-rgb) / 0.12);
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
  border-radius: 8px;
  outline: none;
}

.auth-switch-host :deep(.text-button:hover) {
  color: rgb(var(--auth-accent-rgb));
}

.auth-switch-host :deep(.text-button:focus-visible) {
  color: rgb(var(--auth-accent-rgb));
  box-shadow: 0 0 0 4px rgb(var(--auth-accent-rgb) / 0.12);
}

.auth-switch-host :deep(.btn-auth) {
  min-height: 52px;
  border: 1px solid rgb(23 23 23 / 0.86);
  border-radius: 15px;
  background: linear-gradient(180deg, #252525, #111);
  color: #fff;
  outline: none;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.12),
    0 10px 24px rgb(23 23 23 / 0.12);
  transition:
    transform 220ms var(--ease-out-soft, ease-out),
    box-shadow 220ms var(--ease-out-soft, ease-out);
}

.auth-switch-host :deep(.btn-auth:hover:not(:disabled)) {
  transform: translateY(-1px);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.18),
    0 14px 34px rgb(23 23 23 / 0.16),
    0 0 0 5px rgb(var(--auth-accent-rgb) / 0.1);
}

.auth-switch-host :deep(.btn-auth:focus-visible) {
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.18),
    0 14px 34px rgb(23 23 23 / 0.16),
    0 0 0 5px rgb(var(--auth-accent-rgb) / 0.16);
}

.auth-switch-host :deep(.btn-auth:disabled) {
  cursor: progress;
  opacity: 0.74;
  transform: none;
}

.auth-switch-host :deep(.auth-divider) {
  margin: 26px 0 14px;
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
  outline: none;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.8);
}

.auth-switch-host :deep(.social-row button:hover) {
  border-color: rgb(var(--auth-accent-rgb) / 0.24);
  background: #fff;
  box-shadow:
    0 12px 24px rgb(23 23 23 / 0.07),
    inset 0 1px 0 rgb(255 255 255 / 0.86);
}

.auth-switch-host :deep(.social-row button:focus-visible) {
  border-color: rgb(var(--auth-accent-rgb) / 0.34);
  background: #fff;
  box-shadow:
    0 12px 24px rgb(23 23 23 / 0.07),
    0 0 0 4px rgb(var(--auth-accent-rgb) / 0.12),
    inset 0 1px 0 rgb(255 255 255 / 0.86);
}

.auth-switch-host :deep(.auth-note) {
  color: var(--color-muted);
  line-height: 1.62;
}

.auth-switch-host.is-register-mode :deep(.auth-form) {
  gap: 13px;
}

.auth-switch-host.is-register-mode :deep(.auth-input) {
  min-height: 48px;
}

.auth-switch-host.is-register-mode :deep(.btn-auth) {
  min-height: 50px;
}

.auth-switch-host.is-register-mode :deep(.auth-note) {
  font-size: 12px;
}
/* ============================================================
   字段级 stagger 编排
   ============================================================ */
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
    opacity 300ms var(--ease-out-soft, ease-out),
    transform 380ms var(--ease-out-soft, ease-out),
    filter 320ms var(--ease-out-soft, ease-out);
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

/* 首次进入：温和错峰 */
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

/* 显影切换时：字段与显影时间线协调，定影式逐项入位 */
.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-heading) {
  transition-delay: 220ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-tabs) {
  transition-delay: 260ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .field-line:nth-of-type(1)) {
  transition-delay: 300ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .field-line:nth-of-type(2)) {
  transition-delay: 340ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .field-line:nth-of-type(3)) {
  transition-delay: 380ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .form-row),
.auth-switch-host.is-developing :deep(.auth-pane.is-active .btn-auth),
.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-note) {
  transition-delay: 420ms;
}

.auth-switch-host.is-developing :deep(.auth-pane.is-active .auth-divider),
.auth-switch-host.is-developing :deep(.auth-pane.is-active .social-row) {
  transition-delay: 460ms;
}

/* 禁用子组件自带动画 */
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
/* ============================================================
   显影关键帧 —— 电影级分层显影序列
   ============================================================ */
@keyframes exposure-layer {
  0%, 100% {
    opacity: 0;
  }

  10%, 80% {
    opacity: 1;
  }
}

@keyframes exposure-paper {
  0%, 100% {
    opacity: 0;
  }

  16% {
    opacity: 0.5;
  }

  60% {
    opacity: 0.3;
  }
}

/* 曝光带：从左扫到右，峰值在中段，尾光衰减 */
@keyframes exposure-sweep {
  0% {
    opacity: 0;
    transform: translate3d(-62%, 0, 0) scaleX(0.5);
  }

  14% {
    opacity: 0.82;
  }

  50% {
    opacity: 0.92;
    transform: translate3d(0%, 0, 0) scaleX(1.1);
  }

  72% {
    opacity: 0.48;
    transform: translate3d(28%, 0, 0) scaleX(0.78);
  }

  100% {
    opacity: 0;
    transform: translate3d(68%, 0, 0) scaleX(0.6);
  }
}

/* 反向：注册→登录，严格镜像 */
@keyframes exposure-sweep-reverse {
  0% {
    opacity: 0;
    transform: translate3d(68%, 0, 0) scaleX(0.6);
  }

  14% {
    opacity: 0.82;
  }

  50% {
    opacity: 0.92;
    transform: translate3d(0%, 0, 0) scaleX(1.1);
  }

  72% {
    opacity: 0.48;
    transform: translate3d(-28%, 0, 0) scaleX(0.78);
  }

  100% {
    opacity: 0;
    transform: translate3d(-62%, 0, 0) scaleX(0.5);
  }
}

/* 扫描线：从左到右带辉光衰减 */
@keyframes exposure-line {
  0% {
    left: 10%;
    opacity: 0;
  }

  14% {
    opacity: 0.8;
  }

  68% {
    left: 86%;
    opacity: 0.42;
  }

  100% {
    left: 94%;
    opacity: 0;
  }
}

@keyframes exposure-line-reverse {
  0% {
    left: 90%;
    opacity: 0;
  }

  14% {
    opacity: 0.8;
  }

  68% {
    left: 14%;
    opacity: 0.42;
  }

  100% {
    left: 6%;
    opacity: 0;
  }
}

/* 显影颗粒：仅在显影期闪烁出现，不残留 */
@keyframes exposure-grain {
  0%, 100% {
    opacity: 0;
  }

  10%, 70% {
    opacity: 0.16;
  }

  30% {
    opacity: 0.22;
  }

  50% {
    opacity: 0.12;
  }
}
/* ============================================================
   响应式
   ============================================================ */
@media (max-width: 900px) {
  .auth-switch-host {
    align-items: start;
    --auth-workbench-shift: 0px;
    --grid-size: 50px;
    --grid-softness: 144px;
    padding: 42px 18px 28px;
  }

  .auth-shell {
    width: min(100%, 520px);
    min-height: auto;
    display: grid;
    grid-template-areas: none;
    gap: 28px;
    place-items: stretch;
  }

  .auth-intro {
    position: relative;
    inset: auto;
    justify-items: center;
    text-align: center;
    max-width: 100%;
    margin: 0 auto;
  }

  .intro-mark {
    width: 50px;
    height: 50px;
    margin-bottom: 16px;
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

  .auth-workbench {
    width: 100%;
    grid-area: auto;
    justify-self: stretch;
    transform: none;
  }
}

@media (max-width: 520px) {
  .auth-switch-host {
    --grid-size: 42px;
    --grid-softness: 124px;
    padding: 24px 12px 16px;
  }

  .auth-shell {
    gap: 14px;
  }

  .intro-mark {
    width: 38px;
    height: 38px;
    margin-bottom: 8px;
    border-radius: 12px;
  }

  .intro-kicker {
    margin-bottom: 4px;
    font-size: 11px;
  }

  .auth-intro h1 {
    font-size: clamp(38px, 15vw, 52px);
  }

  .auth-intro p,
  .intro-badges {
    display: none;
  }

  .auth-switch-host :deep(.auth-card) {
    padding: 20px 18px;
    border-radius: 18px;
  }

  .auth-switch-host :deep(.auth-heading) {
    margin-bottom: 14px;
  }

  .auth-switch-host :deep(.auth-heading h2) {
    margin: 5px 0 6px;
    font-size: 25px;
  }

  .auth-switch-host :deep(.auth-heading p) {
    font-size: 13px;
    line-height: 1.48;
  }

  .auth-switch-host :deep(.auth-tabs) {
    margin-bottom: 16px;
  }

  .auth-switch-host :deep(.auth-form),
  .auth-switch-host.is-register-mode :deep(.auth-form) {
    gap: 8px;
  }

  .auth-switch-host :deep(.auth-input),
  .auth-switch-host.is-register-mode :deep(.auth-input) {
    min-height: 44px;
    border-radius: 13px;
  }

  .auth-switch-host :deep(.input-error) {
    min-height: 14px;
    font-size: 11px;
    line-height: 1.24;
  }

  .auth-switch-host.is-register-mode :deep(.auth-card) {
    padding-block: 18px;
  }

  .auth-switch-host.is-register-mode :deep(.btn-auth) {
    min-height: 46px;
  }

  .auth-switch-host.is-register-mode :deep(.auth-note) {
    margin-top: 14px;
    line-height: 1.48;
  }

  .auth-switch-host :deep(.social-row) {
    grid-template-columns: 1fr;
  }

  .auth-exposure-layer {
    inset: -8px;
    border-radius: 20px;
  }
}

/* ============================================================
   无障碍：prefers-reduced-motion 全部降为静态
   ============================================================ */
@media (prefers-reduced-motion: reduce) {
  .auth-canvas-primary,
  .auth-canvas-grid--far,
  .auth-canvas-grid--main,
  .auth-canvas-grid--main::before,
  .auth-canvas-grid--main::after,
  .auth-preview-fade-enter-active,
  .auth-preview-fade-leave-active,
  .auth-scene-fade-enter-active,
  .auth-scene-fade-leave-active,
  .auth-exposure-layer,
  .auth-exposure-layer span,
  .auth-canvas-grain,
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
    transition: none !important;
    transform: none !important;
    filter: none !important;
  }

  /* 网格降为静态：隐藏交互层，仅保留安静常驻层 */
  .auth-canvas-grid--main::before,
  .auth-canvas-grid--main::after,
  .auth-canvas-grain {
    display: none;
  }

  .auth-canvas-grid--far,
  .auth-canvas-grid--main {
    opacity: 0.18;
  }
}
</style>
