<template>
  <div class="app-shell" :class="{ 'has-app-nav': showAppNav }">
    <div class="noise-overlay"></div>
    <CustomCursor />
    <NavBar v-if="showAppNav" />
    <router-view v-slot="{ Component }">
      <KeepAlive include="Home,History,Recharge" :max="3">
        <component :is="Component" />
      </KeepAlive>
    </router-view>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import CustomCursor from './components/CustomCursor.vue'
import NavBar from './components/NavBar.vue'

const route = useRoute()
const showAppNav = computed(() => Boolean(route.meta.requiresAuth))

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
  opacity: 0.012;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.app-shell.has-app-nav :deep(.paper-page) {
  min-height: calc(100vh - 69px);
}

@media (max-width: 760px) {
  .app-shell.has-app-nav :deep(.paper-page) {
    min-height: calc(100vh - 63px);
  }
}
</style>
