<template>
  <div class="app-shell">
    <div class="noise-overlay"></div>
    <CustomCursor />
    <router-view v-slot="{ Component }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import CustomCursor from './components/CustomCursor.vue'

onMounted(() => {
  document.addEventListener('contextmenu', preventBrowserContextMenu)
  document.addEventListener('dblclick', preventPageDoubleClickSelection, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('contextmenu', preventBrowserContextMenu)
  document.removeEventListener('dblclick', preventPageDoubleClickSelection, true)
})

function preventBrowserContextMenu(event) {
  if (isEditableTarget(event.target)) return
  event.preventDefault()
}

function preventPageDoubleClickSelection(event) {
  if (isEditableTarget(event.target)) return
  event.preventDefault()
  window.getSelection?.().removeAllRanges()
}

function isEditableTarget(target) {
  return Boolean(target?.closest?.('input, textarea, select, [contenteditable=""], [contenteditable="true"]'))
}
</script>

<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  background: var(--color-paper);
}

.noise-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.018;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
</style>
