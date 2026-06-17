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
const hoveringInteractive = ref(false)
const hoveringInput = ref(false)
const pressing = ref(false)
const dotEl = ref(null)

const target = { x: 0, y: 0 }
const dot = { x: 0, y: 0 }
const previousDot = { x: 0, y: 0 }
let mediaQuery = null
let rafId = 0

const cursorClass = computed(() => ({
  'is-interactive': hoveringInteractive.value,
  'is-input': hoveringInput.value,
  'is-pressing': pressing.value
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
  window.addEventListener('blur', handlePointerUp)
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener?.('change', updateEnabled)
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerover', handlePointerOver)
  window.removeEventListener('pointerout', handlePointerOut)
  window.removeEventListener('pointerdown', handlePointerDown)
  window.removeEventListener('pointerup', handlePointerUp)
  window.removeEventListener('blur', handlePointerUp)
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
  }
}

function handlePointerMove(event) {
  if (!enabled.value) return
  target.x = event.clientX
  target.y = event.clientY
  if (!cursorReady.value) {
    dot.x = target.x
    dot.y = target.y
    cursorReady.value = true
  }
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
    return
  }
  updateHoverState(event.relatedTarget)
}

function handlePointerDown(event) {
  if (!enabled.value) return
  pressing.value = true
}

function handlePointerUp() {
  pressing.value = false
}

function updateHoverState(targetElement) {
  hoveringInput.value = Boolean(targetElement?.closest?.(INPUT_SELECTOR))
  hoveringInteractive.value = Boolean(targetElement?.closest?.(INTERACTIVE_SELECTOR))
}

function renderCursor() {
  if (!enabled.value) return

  previousDot.x = dot.x
  previousDot.y = dot.y
  dot.x += (target.x - dot.x) * 0.26
  dot.y += (target.y - dot.y) * 0.26

  if (dotEl.value) {
    const vx = dot.x - previousDot.x
    const vy = dot.y - previousDot.y
    const speed = Math.min(1, Math.hypot(vx, vy) / 42)
    const angle = Math.atan2(vy, vx) * 180 / Math.PI
    const stretch = hoveringInput.value ? 1 : 1 + speed * 0.32
    const squash = hoveringInput.value ? 1 : 1 - speed * 0.12
    dotEl.value.style.transform = `translate3d(${dot.x}px, ${dot.y}px, 0) rotate(${angle}deg) scale(${stretch}, ${squash})`
    dotEl.value.style.opacity = String(0.68 + speed * 0.18)
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
