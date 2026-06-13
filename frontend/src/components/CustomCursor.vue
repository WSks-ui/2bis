<template>
  <Teleport to="body">
    <div v-if="enabled" ref="pulseRoot" class="cursor-pulse-root" aria-hidden="true">
      <span ref="pulseEl" class="cursor-pulse"></span>
    </div>
  </Teleport>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const enabled = ref(false)
const pulseRoot = ref(null)
const pulseEl = ref(null)

let mediaQuery = null
let pulseTimer = null

onMounted(() => {
  mediaQuery = window.matchMedia('(hover: hover) and (pointer: fine)')
  updateEnabled()
  mediaQuery.addEventListener?.('change', updateEnabled)

  window.addEventListener('pointerdown', showPulse, { passive: true })
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener?.('change', updateEnabled)
  window.removeEventListener('pointerdown', showPulse)
  clearTimeout(pulseTimer)
  document.documentElement.classList.remove('has-custom-cursor')
})

function updateEnabled() {
  enabled.value = Boolean(mediaQuery?.matches)
  document.documentElement.classList.toggle('has-custom-cursor', enabled.value)
}

function showPulse(event) {
  if (!enabled.value || !pulseRoot.value || !pulseEl.value) return

  pulseRoot.value.style.transform = `translate3d(${event.clientX}px, ${event.clientY}px, 0)`
  pulseEl.value.classList.remove('is-active')
  clearTimeout(pulseTimer)

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      pulseEl.value?.classList.add('is-active')
      pulseTimer = setTimeout(() => {
        pulseEl.value?.classList.remove('is-active')
      }, 380)
    })
  })
}
</script>

<style scoped>
.cursor-pulse-root {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 10000;
  width: 1px;
  height: 1px;
  pointer-events: none;
  contain: layout style paint;
  transform-origin: 0 0;
  will-change: transform;
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

.cursor-pulse.is-active {
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
