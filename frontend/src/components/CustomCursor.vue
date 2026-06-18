<template>
  <Teleport to="body">
    <div v-if="enabled" class="cursor-layer" :class="{ 'is-ready': cursorReady }" aria-hidden="true">
      <span ref="dotEl" class="cursor-dot" :class="cursorClass"></span>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const INTERACTIVE_SELECTOR = [
  'a[href]',
  'button:not(:disabled)',
  '[role="button"]:not([aria-disabled="true"])',
  '[data-cursor="interactive"]'
].join(',')
const INPUT_SELECTOR = 'input, textarea, select, [contenteditable=""], [contenteditable="true"]'

const enabled = ref(false)
const cursorReady = ref(false)
const cursorIdle = ref(false)
const hoveringInteractive = ref(false)
const hoveringInput = ref(false)
const pressing = ref(false)
const dotEl = ref(null)

const target = { x: 0, y: 0 }
const dot = { x: 0, y: 0 }
const previousDot = { x: 0, y: 0 }
const magnetic = { x: 0, y: 0, active: false, strength: 0 }
let mediaQuery = null
let rafId = 0
let idleTimer = 0

const cursorClass = computed(() => ({
  'is-interactive': hoveringInteractive.value,
  'is-input': hoveringInput.value,
  'is-pressing': pressing.value,
  'is-idle': cursorIdle.value
}))

onMounted(() => {
  mediaQuery = window.matchMedia('(hover: hover) and (pointer: fine)')
  updateEnabled()
  mediaQuery.addEventListener?.('change', updateEnabled)

  window.addEventListener('pointermove', handlePointerMove, { passive: true })
  window.addEventListener('pointerover', handlePointerOver, { passive: true })
  window.addEventListener('pointerout', handlePointerOut, { passive: true })
  window.addEventListener('pointerdown', handlePointerDown, { passive: true })
  window.addEventListener('pointerup', handlePointerUp, { passive: true })
  window.addEventListener('scroll', handleScroll, { passive: true })
  window.addEventListener('blur', handlePointerUp)
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener?.('change', updateEnabled)
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerover', handlePointerOver)
  window.removeEventListener('pointerout', handlePointerOut)
  window.removeEventListener('pointerdown', handlePointerDown)
  window.removeEventListener('pointerup', handlePointerUp)
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('blur', handlePointerUp)
  window.clearTimeout(idleTimer)
  cancelAnimationFrame(rafId)
  document.documentElement.classList.remove('has-custom-cursor')
})

function updateEnabled() {
  enabled.value = Boolean(mediaQuery?.matches)
  document.documentElement.classList.toggle('has-custom-cursor', enabled.value)
  if (enabled.value && !rafId) {
    rafId = requestAnimationFrame(renderCursor)
  } else if (!enabled.value) {
    cancelAnimationFrame(rafId)
    rafId = 0
    cursorReady.value = false
    cursorIdle.value = false
    magnetic.active = false
  }
}

function handlePointerMove(event) {
  if (!enabled.value) return
  target.x = event.clientX
  target.y = event.clientY
  updateHoverState(event.target)

  if (!cursorReady.value) {
    dot.x = target.x
    dot.y = target.y
    previousDot.x = target.x
    previousDot.y = target.y
    cursorReady.value = true
  }

  updateMagneticTarget(event.target)
  scheduleIdle()
}

function handlePointerOver(event) {
  if (!enabled.value) return
  updateHoverState(event.target)
}

function handlePointerOut(event) {
  if (!enabled.value) return
  if (!event.relatedTarget) {
    hoveringInteractive.value = false
    hoveringInput.value = false
    magnetic.active = false
    cursorReady.value = false
    cursorIdle.value = false
    return
  }
  updateHoverState(event.relatedTarget)
}

function handlePointerDown() {
  if (!enabled.value) return
  pressing.value = true
  cursorIdle.value = false
}

function handlePointerUp() {
  pressing.value = false
}

function handleScroll() {
  magnetic.active = false
}

function updateHoverState(targetElement) {
  hoveringInput.value = Boolean(targetElement?.closest?.(INPUT_SELECTOR))
  hoveringInteractive.value = Boolean(targetElement?.closest?.(INTERACTIVE_SELECTOR))
}

function updateMagneticTarget(targetElement) {
  const interactiveElement = targetElement?.closest?.(INTERACTIVE_SELECTOR)
  const inputElement = targetElement?.closest?.(INPUT_SELECTOR)
  if (!interactiveElement || inputElement) {
    magnetic.active = false
    return
  }

  const rect = interactiveElement.getBoundingClientRect()
  if (!rect.width || !rect.height) {
    magnetic.active = false
    return
  }

  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  const distance = Math.hypot(target.x - centerX, target.y - centerY)
  const radius = Math.min(130, Math.max(54, Math.max(rect.width, rect.height) * 0.62))
  const strength = Math.max(0, 1 - distance / radius)

  magnetic.active = strength > 0
  magnetic.strength = strength
  magnetic.x = centerX
  magnetic.y = centerY
}

function scheduleIdle() {
  cursorReady.value = true
  cursorIdle.value = false
  window.clearTimeout(idleTimer)
  idleTimer = window.setTimeout(() => {
    cursorIdle.value = true
    magnetic.active = false
  }, 1800)
}

function renderCursor() {
  if (!enabled.value) return

  previousDot.x = dot.x
  previousDot.y = dot.y
  // 轻磁性只影响光标小球，不移动真实鼠标，避免破坏表单和点击可预期性。
  const magneticPull = magnetic.active ? magnetic.strength * 0.18 : 0
  const renderTargetX = target.x + (magnetic.x - target.x) * magneticPull
  const renderTargetY = target.y + (magnetic.y - target.y) * magneticPull
  const follow = pressing.value ? 0.38 : hoveringInteractive.value ? 0.3 : 0.24
  dot.x += (renderTargetX - dot.x) * follow
  dot.y += (renderTargetY - dot.y) * follow

  if (dotEl.value) {
    const vx = dot.x - previousDot.x
    const vy = dot.y - previousDot.y
    const speed = Math.min(1, Math.hypot(vx, vy) / 42)
    const angle = Math.atan2(vy, vx) * 180 / Math.PI
    const magnetScale = magnetic.active ? magnetic.strength * 0.18 : 0
    const pressScale = pressing.value ? -0.12 : 0
    const stretch = hoveringInput.value ? 1 : 1 + speed * 0.32 + magnetScale + pressScale
    const squash = hoveringInput.value ? 1 : 1 - speed * 0.12 - magnetScale * 0.18 + pressScale
    dotEl.value.style.transform = `translate3d(${dot.x}px, ${dot.y}px, 0) rotate(${angle}deg) scale(${stretch}, ${squash})`
    const opacity = cursorIdle.value ? 0.42 : 0.68 + speed * 0.18
    dotEl.value.style.opacity = String(opacity)
  }

  rafId = requestAnimationFrame(renderCursor)
}
</script>

<style scoped>
.cursor-layer {
  position: fixed;
  inset: 0;
  z-index: 10000;
  pointer-events: none;
  contain: strict;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.cursor-layer.is-ready {
  opacity: 1;
}

.cursor-dot {
  position: fixed;
  top: 0;
  left: 0;
  pointer-events: none;
  will-change: transform, opacity, width, height;
}

.cursor-dot {
  width: 9px;
  height: 9px;
  margin: -4.5px 0 0 -4.5px;
  border-radius: 50%;
  background: rgba(23, 23, 23, 0.88);
  box-shadow:
    0 0 0 3px rgba(255, 255, 255, 0.55),
    0 8px 18px rgba(23, 23, 23, 0.16);
  opacity: 0.78;
  transition:
    width 160ms var(--ease-spring),
    height 160ms var(--ease-spring),
    margin 160ms var(--ease-spring),
    opacity var(--transition-base),
    background var(--transition-base),
    box-shadow var(--transition-base);
}

.cursor-dot.is-interactive {
  width: 13px;
  height: 13px;
  margin: -6.5px 0 0 -6.5px;
  background: var(--color-blue);
  box-shadow:
    0 0 0 4px rgba(60, 110, 232, 0.1),
    0 10px 22px rgba(60, 110, 232, 0.18);
  opacity: 0.9;
}

.cursor-dot.is-input {
  width: 4px;
  height: 20px;
  margin: -10px 0 0 -2px;
  border-radius: 999px;
  background: rgba(23, 23, 23, 0.58);
  box-shadow: none;
  opacity: 0.72;
}

.cursor-dot.is-pressing {
  width: 10px;
  height: 10px;
  margin: -5px 0 0 -5px;
}

@media (prefers-reduced-motion: reduce) {
  .cursor-layer {
    display: none;
  }
}
</style>
