import { onBeforeUnmount, ref } from 'vue'

const SPRING = 0.16
const FRICTION = 0.76
const IDLE_EPSILON = 0.002

export function useShowcaseParallax() {
  const showcaseRef = ref(null)
  let frameId = 0
  let isActive = false
  let lastTime = 0
  let reduceMotion = false

  const pointer = {
    targetX: 0,
    targetY: 0,
    currentX: 0,
    currentY: 0,
    velocityX: 0,
    velocityY: 0
  }

  if (typeof window !== 'undefined' && window.matchMedia) {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  function shouldTrack(event) {
    if (reduceMotion) return false
    if ('pointerType' in event) {
      return event.pointerType === 'mouse' || event.pointerType === 'pen'
    }
    return event.type.startsWith('mouse')
  }

  function setShowcaseVars(showcase, speed) {
    const x = Math.max(-1, Math.min(1, pointer.currentX))
    const y = Math.max(-1, Math.min(1, pointer.currentY))
    const energy = Math.min(1, Math.hypot(x, y) * 0.72 + speed * 2.4)

    showcase.style.setProperty('--showcase-bg-x', `${(-x * 18).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-bg-y', `${(-y * 14).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-poster-x', `${(x * 24).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-poster-y', `${(y * 18).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-poster-rotate', `${(2.5 + x * 1.8).toFixed(2)}deg`)
    showcase.style.setProperty('--showcase-frame-primary-x', `${(-x * 15).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-frame-primary-y', `${(-y * 10).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-frame-secondary-x', `${(x * 12).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-frame-secondary-y', `${(y * 8).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-copy-x', `${(x * 7).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-copy-y', `${(y * 5).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-logo-x', `${(x * 5).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-logo-y', `${(y * 4).toFixed(2)}px`)
    showcase.style.setProperty('--showcase-glow-x', `${(50 + x * 24).toFixed(2)}%`)
    showcase.style.setProperty('--showcase-glow-y', `${(48 + y * 18).toFixed(2)}%`)
    showcase.style.setProperty('--showcase-energy', energy.toFixed(3))
  }

  function tick(time) {
    const showcase = showcaseRef.value
    if (!showcase) {
      frameId = 0
      return
    }

    const delta = lastTime ? Math.min(32, time - lastTime) / 16.67 : 1
    lastTime = time

    // 使用弹簧插值生成“柔性跟随”，让内容有惯性而不是直接贴住鼠标。
    pointer.velocityX = (pointer.velocityX + (pointer.targetX - pointer.currentX) * SPRING * delta) * FRICTION
    pointer.velocityY = (pointer.velocityY + (pointer.targetY - pointer.currentY) * SPRING * delta) * FRICTION
    pointer.currentX += pointer.velocityX * delta
    pointer.currentY += pointer.velocityY * delta

    const speed = Math.hypot(pointer.velocityX, pointer.velocityY)
    setShowcaseVars(showcase, speed)

    const isSettled =
      !isActive &&
      speed < IDLE_EPSILON &&
      Math.abs(pointer.targetX - pointer.currentX) < IDLE_EPSILON &&
      Math.abs(pointer.targetY - pointer.currentY) < IDLE_EPSILON

    if (isSettled) {
      showcase.classList.remove('is-showcase-active')
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

  function syncTargetFromEvent(event) {
    const rect = event.currentTarget.getBoundingClientRect()
    const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2
    const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2
    pointer.targetX = Math.max(-1, Math.min(1, x))
    pointer.targetY = Math.max(-1, Math.min(1, y))
  }

  function handleShowcaseEnter(event) {
    if (!shouldTrack(event)) return

    isActive = true
    event.currentTarget.classList.add('is-showcase-active')
    syncTargetFromEvent(event)
    ensureAnimation()
  }

  function handleShowcaseMove(event) {
    if (!shouldTrack(event)) return

    isActive = true
    event.currentTarget.classList.add('is-showcase-active')
    syncTargetFromEvent(event)
    ensureAnimation()
  }

  function handleShowcaseLeave() {
    isActive = false
    pointer.targetX = 0
    pointer.targetY = 0
    ensureAnimation()
  }

  onBeforeUnmount(() => {
    if (frameId) {
      cancelAnimationFrame(frameId)
    }
  })

  return {
    showcaseRef,
    handleShowcaseEnter,
    handleShowcaseMove,
    handleShowcaseLeave
  }
}
