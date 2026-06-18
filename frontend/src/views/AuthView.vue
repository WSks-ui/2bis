<template>
  <div class="auth-switch-host" :class="{ 'is-login-mode': isLogin, 'is-register-mode': isRegister }">
    <div class="auth-panel-bridge" aria-hidden="true"></div>
    <Login
      class="auth-pane"
      :show-showcase="true"
      :class="{ 'is-active': isLogin, 'is-inactive': !isLogin }"
      :aria-hidden="String(!isLogin)"
    />
    <Register
      class="auth-pane"
      :show-showcase="false"
      :class="{ 'is-active': isRegister, 'is-inactive': !isRegister }"
      :aria-hidden="String(!isRegister)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAdaptiveAuthTheme } from '../composables/useAdaptiveAuthTheme'
import Login from './Login.vue'
import Register from './Register.vue'

defineOptions({ name: 'AuthView' })

const route = useRoute()
const isRegister = computed(() => route.name === 'Register')
const isLogin = computed(() => !isRegister.value)

useAdaptiveAuthTheme({
  imageSelector: '.auth-page-login .showcase-image'
})
</script>

<style scoped>
.auth-switch-host {
  position: relative;
  min-height: 100vh;
  --auth-accent-rgb: 72 147 90;
  --auth-warm-rgb: 166 201 191;
  --auth-panel-bg-start: hsl(134deg 14% 99%);
  --auth-panel-bg-mid: hsl(134deg 16% 96%);
  --auth-panel-bg-end: hsl(162deg 12% 93%);
  --auth-card-bg: rgba(255, 255, 255, 0.82);
  --auth-control-bg: hsl(134deg 10% 94%);
  --auth-control-bg-strong: hsl(134deg 9% 91%);
  --auth-panel-line: rgb(72 147 90 / 0.16);
  --auth-panel-shadow: rgb(72 147 90 / 0.12);
  overflow: hidden;
  background:
    radial-gradient(circle at 78% 18%, rgb(var(--auth-accent-rgb) / 0.12), transparent 22rem),
    linear-gradient(135deg, var(--auth-panel-bg-start), var(--auth-panel-bg-end));
  transition:
    background 520ms var(--transition-slow),
    filter 360ms var(--ease-out-soft);
}

.auth-switch-host::before,
.auth-panel-bridge {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.auth-switch-host::before {
  z-index: 2;
  opacity: 0.54;
  background:
    radial-gradient(circle at 62% 42%, rgb(var(--auth-accent-rgb) / 0.1), transparent 18rem),
    linear-gradient(90deg, transparent 0 51%, rgb(var(--auth-accent-rgb) / 0.05) 58%, transparent 76%);
  mix-blend-mode: multiply;
  transition:
    opacity 420ms var(--transition-slow),
    transform 520ms var(--ease-out-soft);
}

.auth-panel-bridge {
  z-index: 5;
  left: calc(58vw - clamp(90px, 8vw, 140px));
  right: auto;
  width: clamp(160px, 14vw, 260px);
  background:
    linear-gradient(
      90deg,
      transparent 0%,
      rgb(var(--auth-warm-rgb) / 0.08) 30%,
      rgb(255 253 250 / 0.58) 68%,
      var(--auth-panel-bg-start) 100%
    );
  filter: blur(0.2px);
  transform: translate3d(0, 0, 0);
  transition:
    opacity 420ms var(--transition-slow),
    transform 520ms var(--ease-out-soft),
    background 520ms var(--transition-slow);
}

.auth-switch-host.is-register-mode::before {
  opacity: 0.68;
  transform: translate3d(10px, 0, 0);
}

.auth-switch-host.is-register-mode .auth-panel-bridge {
  transform: translate3d(8px, 0, 0);
}

.auth-switch-host :deep(.auth-pane) {
  position: absolute;
  inset: 0;
  width: 100%;
  min-height: 100vh;
  background: transparent !important;
  pointer-events: none;
}

.auth-switch-host :deep(.auth-pane.is-active) {
  position: relative;
  z-index: 3;
}

.auth-switch-host :deep(.auth-pane.is-inactive) {
  z-index: 1;
}

.auth-switch-host :deep(.auth-page-login .auth-showcase) {
  position: relative;
  z-index: 4;
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

/* 左侧展示区只保留登录页这一份，切换时固定不动，避免用户误以为整页重新加载。 */
.auth-switch-host :deep(.auth-page-register .auth-panel) {
  grid-column: 2;
}

.auth-switch-host :deep(.auth-panel) {
  position: relative;
  z-index: 6;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translate3d(24px, 0, 0) scale(0.986);
  filter: blur(8px);
  transition:
    opacity 240ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 360ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 320ms cubic-bezier(0.16, 1, 0.3, 1),
    visibility 0s linear 320ms;
}

.auth-switch-host :deep(.auth-pane.is-active .auth-panel) {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translate3d(0, 0, 0) scale(1);
  filter: blur(0);
  transition:
    opacity 260ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 380ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 340ms cubic-bezier(0.16, 1, 0.3, 1);
}

.auth-switch-host :deep(.auth-pane.is-inactive .auth-panel) {
  transform: translate3d(-18px, 0, 0) scale(1.006);
}

.auth-switch-host :deep(.auth-card) {
  transform-origin: center right;
  transition:
    transform 420ms var(--ease-out-soft),
    box-shadow 420ms var(--transition-slow),
    border-color 420ms var(--transition-slow);
}

.auth-switch-host :deep(.auth-pane.is-active .auth-card) {
  transform: translate3d(0, 0, 0) rotateY(0deg);
}

.auth-switch-host :deep(.auth-pane.is-inactive .auth-card) {
  transform: translate3d(-8px, 0, 0) rotateY(-3deg);
}

.auth-switch-host :deep(.auth-heading),
.auth-switch-host :deep(.auth-tabs),
.auth-switch-host :deep(.field-line),
.auth-switch-host :deep(.form-row),
.auth-switch-host :deep(.btn-auth),
.auth-switch-host :deep(.auth-divider),
.auth-switch-host :deep(.social-row),
.auth-switch-host :deep(.auth-note) {
  transition:
    opacity 320ms var(--ease-out-soft),
    transform 360ms var(--ease-out-soft),
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
  transform: translate3d(10px, 0, 0);
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
  transition-delay: 124ms;
}

/* 认证壳负责切换动画，子页面入场动画在这里关闭，避免切换像整页重载。 */
.auth-switch-host :deep(.auth-page),
.auth-switch-host :deep(.auth-showcase),
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
.auth-switch-host :deep(.auth-note),
.auth-switch-host :deep(.showcase-logo),
.auth-switch-host :deep(.showcase-copy),
.auth-switch-host :deep(.showcase-poster),
.auth-switch-host :deep(.art-frame) {
  animation: none !important;
}

@media (prefers-reduced-motion: reduce) {
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
    transition: none;
    transform: none;
    filter: none;
  }
}

@media (max-width: 980px) {
  .auth-panel-bridge {
    display: none;
  }

  .auth-switch-host :deep(.auth-page-register .auth-panel) {
    grid-column: 1;
  }
}
</style>
