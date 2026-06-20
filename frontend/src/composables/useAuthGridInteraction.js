import { onBeforeUnmount, ref } from 'vue'

const SPRING = 0.22
const FRICTION = 0.72
const IDLE_EPSILON = 0.018

export function useAuthGridInteraction() {
  const authPanelRef = ref(null)
  const isGridActive = ref(false)
  let frameId = 0
  let isActive = false
  let lastTime = 0
  let interactionTarget = null

  const pointer = {
    targetX: 50,
    targetY: 50,
    currentX: 50,
    currentY: 50,
    velocityX: 0,
    velocityY: 0
  }

  function shouldTrack(event) {
    return event.pointerType === 'mouse' || event.pointerType === 'pen'
  }

  function setPanelVars(panel, speed) {
    const pullX = pointer.targetX - pointer.currentX
    const pullY = pointer.targetY - pointer.currentY
    const intensity = Math.min(1, Math.max(speed / 1.8, Math.hypot(pullX, pullY) / 16))
    const stretch = 1 + intensity * 0.075
    const skewX = Math.max(-14, Math.min(14, pullX * 0.18 + pointer.velocityX * 0.9))
    const skewY = Math.max(-14, Math.min(14, pullY * 0.18 + pointer.velocityY * 0.9))
    const tailX = pointer.currentX - pointer.velocityX * 2.3
    const tailY = pointer.currentY - pointer.velocityY * 2.3

    panel.style.setProperty('--grid-x', `${pointer.currentX}%`)
    panel.style.setProperty('--grid-y', `${pointer.currentY}%`)
    panel.style.setProperty('--grid-target-x', `${pointer.targetX}%`)
    panel.style.setProperty('--grid-target-y', `${pointer.targetY}%`)
    panel.style.setProperty('--grid-tail-x', `${Math.min(100, Math.max(0, tailX))}%`)
    panel.style.setProperty('--grid-tail-y', `${Math.min(100, Math.max(0, tailY))}%`)
    panel.style.setProperty('--grid-warp-x', `${skewX}px`)
    panel.style.setProperty('--grid-warp-y', `${skewY}px`)
    panel.style.setProperty('--grid-stretch-x', stretch.toFixed(3))
    panel.style.setProperty('--grid-stretch-y', (1 + intensity * 0.028).toFixed(3))
    panel.style.setProperty('--grid-tilt', `${Math.max(-6, Math.min(6, skewX * 0.34))}deg`)
    panel.style.setProperty('--grid-softness', `${132 + intensity * 86}px`)
  }

  function resolvePanel(event) {
    const closestTarget = event?.target?.closest?.('.auth-switch-host, .auth-panel')
    const panel = authPanelRef.value || event?.currentTarget || closestTarget || interactionTarget
    interactionTarget = panel || null
    return panel
  }

  function tick(time) {
    const panel = resolvePanel()
    if (!panel) {
      frameId = 0
      return
    }

    const delta = lastTime ? Math.min(32, time - lastTime) / 16.67 : 1
    lastTime = time

    // 保持双轴弹性速度独立更新，让背景网格同时具备拖拽形变和尾迹。
    pointer.velocityX = (pointer.velocityX + (pointer.targetX - pointer.currentX) * SPRING * delta) * FRICTION
    pointer.velocityY = (pointer.velocityY + (pointer.targetY - pointer.currentY) * SPRING * delta) * FRICTION
    pointer.currentX += pointer.velocityX * delta
    pointer.currentY += pointer.velocityY * delta

    const speed = Math.hypot(pointer.velocityX, pointer.velocityY)
    setPanelVars(panel, speed)

    const isSettled =
      !isActive &&
      speed < IDLE_EPSILON &&
      Math.abs(pointer.targetX - pointer.currentX) < IDLE_EPSILON &&
      Math.abs(pointer.targetY - pointer.currentY) < IDLE_EPSILON

    if (isSettled) {
      panel.classList.remove('is-grid-active')
      isGridActive.value = false
      frameId = 0
      lastTime = 0
      return
    }

    frameId = requestAnimationFrame(tick)
  }

  function ensureAnimation() {
    if (!frameId) {
      frameId = requestAnimationFrame(tick)
    }
  }

  function syncTargetFromEvent(event, panel = resolvePanel(event)) {
    if (!panel) return

    const rect = panel.getBoundingClientRect()
    pointer.targetX = Math.min(100, Math.max(0, ((event.clientX - rect.left) / rect.width) * 100))
    pointer.targetY = Math.min(100, Math.max(0, ((event.clientY - rect.top) / rect.height) * 100))
  }

  function handleGridEnter(event) {
    if (!shouldTrack(event)) return

    const panel = resolvePanel(event)
    isActive = true
    isGridActive.value = true
    panel?.classList.add('is-grid-active')
    syncTargetFromEvent(event, panel)
    if (panel) setPanelVars(panel, 0)
    ensureAnimation()
  }

  function handleGridMove(event) {
    if (!shouldTrack(event)) return

    const panel = resolvePanel(event)
    isActive = true
    isGridActive.value = true
    panel?.classList.add('is-grid-active')
    syncTargetFromEvent(event, panel)
    ensureAnimation()
  }

  function handleGridLeave(event) {
    isActive = false
    const panel = resolvePanel(event)
    if (!panel) return

    const rect = panel.getBoundingClientRect()
    pointer.targetX = Math.min(100, Math.max(0, ((event.clientX - rect.left) / rect.width) * 100))
    pointer.targetY = Math.min(100, Math.max(0, ((event.clientY - rect.top) / rect.height) * 100))
    if (panel) setPanelVars(panel, 0)
    ensureAnimation()
  }

  onBeforeUnmount(() => {
    if (frameId) {
      cancelAnimationFrame(frameId)
    }
  })

  return {
    authPanelRef,
    handleGridEnter,
    handleGridMove,
    handleGridLeave,
    isGridActive
  }
}
