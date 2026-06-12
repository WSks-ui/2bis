<template>
  <div
    v-if="enabled"
    class="custom-cursor"
    :class="{
      'custom-cursor--visible': visible,
      'custom-cursor--interactive': interactive,
      'custom-cursor--pressed': pressed,
      'custom-cursor--pulse': pulseActive
    }"
    aria-hidden="true"
  >
    <div class="cursor-anchor" :style="cursorStyle">
      <span class="cursor-pulse"></span>
      <svg class="cursor-pointer" viewBox="0 0 24 32" fill="none">
        <path
          class="cursor-shape"
          d="M3.1 2.55C2.63 2.16 1.9 2.5 1.9 3.12V28.1C1.9 28.78 2.76 29.08 3.18 28.54L9.18 20.88C9.42 20.57 9.82 20.42 10.2 20.5L19.92 22.44C20.6 22.58 21.03 21.77 20.54 21.28L3.1 2.55Z"
        />
      </svg>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const enabled = ref(false)
const visible = ref(false)
const interactive = ref(false)
const pressed = ref(false)
const pulseActive = ref(false)
const position = ref({ x: 0, y: 0 })

let mediaQuery = null
let pulseTimer = null

const cursorStyle = computed(() => ({
  transform: `translate3d(${position.value.x}px, ${position.value.y}px, 0)`
}))

onMounted(() => {
  mediaQuery = window.matchMedia('(hover: hover) and (pointer: fine)')
  updateEnabled()
  mediaQuery.addEventListener?.('change', updateEnabled)

  window.addEventListener('pointermove', handlePointerMove, { passive: true })
  window.addEventListener('pointerleave', hideCursor)
  window.addEventListener('pointerdown', markPressed, { passive: true })
  window.addEventListener('pointerup', releasePressed, { passive: true })
  window.addEventListener('pointercancel', releasePressed, { passive: true })
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener?.('change', updateEnabled)
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerleave', hideCursor)
  window.removeEventListener('pointerdown', markPressed)
  window.removeEventListener('pointerup', releasePressed)
  window.removeEventListener('pointercancel', releasePressed)
  clearTimeout(pulseTimer)
  document.documentElement.classList.remove('has-custom-cursor')
})

function updateEnabled() {
  enabled.value = Boolean(mediaQuery?.matches)
  document.documentElement.classList.toggle('has-custom-cursor', enabled.value)
  if (!enabled.value) hideCursor()
}

function handlePointerMove(event) {
  if (!enabled.value) return
  position.value = { x: event.clientX, y: event.clientY }
  visible.value = true
  updateTargetState(event)
}

function updateTargetState(event) {
  const target = event.target
  interactive.value = isInteractiveTarget(target)
}

function markPressed(event) {
  updateTargetState(event)
  pressed.value = true
  pulseActive.value = false
  clearTimeout(pulseTimer)
  requestAnimationFrame(() => {
    pulseActive.value = true
    pulseTimer = setTimeout(() => {
      pulseActive.value = false
    }, 380)
  })
}

function releasePressed(event) {
  pressed.value = false
  updateTargetState(event)
}

function hideCursor() {
  visible.value = false
  interactive.value = false
  pressed.value = false
  pulseActive.value = false
}

function isInteractiveTarget(target) {
  return Boolean(target?.closest?.('a, button, [role="button"], input, textarea, select, label, .task-card, .surface-card'))
}
</script>

<style scoped>
.custom-cursor {
  position: fixed;
  inset: 0;
  z-index: 10000;
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.custom-cursor--visible {
  opacity: 1;
}

.cursor-anchor {
  position: fixed;
  top: 0;
  left: 0;
  width: 1px;
  height: 1px;
  pointer-events: none;
  transform-origin: 0 0;
  will-change: transform;
}

.cursor-pointer {
  position: absolute;
  top: 0;
  left: 0;
  width: 24px;
  height: 32px;
  pointer-events: none;
  overflow: visible;
  transform-origin: 2px 2px;
  --cursor-rotation: -15deg;
  transform: rotate(var(--cursor-rotation));
  will-change: transform, opacity, filter;
  filter: drop-shadow(0 1px 0 rgba(23, 23, 23, 0.2));
  transition:
    filter var(--transition-base),
    opacity var(--transition-base),
    transform 180ms cubic-bezier(0.2, 0.9, 0.24, 1.2);
}

.cursor-pulse {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 28px;
  height: 28px;
  border: 1px solid rgba(60, 110, 232, 0.28);
  border-radius: 50%;
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.4);
  transform-origin: center;
  pointer-events: none;
}

.cursor-shape {
  fill: #ffffff;
  stroke: rgba(17, 17, 17, 0.98);
  stroke-width: 2.1;
  stroke-linejoin: round;
  shape-rendering: geometricPrecision;
  vector-effect: non-scaling-stroke;
}

.custom-cursor--interactive .cursor-pointer {
  transform: rotate(var(--cursor-rotation)) scale(1.08);
  filter: drop-shadow(0 2px 1px rgba(23, 23, 23, 0.22));
}

.custom-cursor--pressed .cursor-pointer {
  opacity: 0.82;
  transform: rotate(var(--cursor-rotation)) scale(0.94);
  filter: drop-shadow(0 1px 0 rgba(23, 23, 23, 0.26));
}

.custom-cursor--pulse .cursor-pulse {
  animation: cursor-pulse 360ms ease-out;
}

@keyframes cursor-pulse {
  0% {
    opacity: 0.34;
    transform: translate(-50%, -50%) scale(0.35);
  }

  100% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(1.35);
  }
}
</style>
