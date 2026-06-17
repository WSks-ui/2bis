const RIPPLE_SELECTOR = [
  'button:not(:disabled)',
  'a[href]',
  '[role="button"]:not([aria-disabled="true"])',
  '[data-ripple]'
].join(',')

const SPOTLIGHT_SELECTOR = [
  '.surface-card',
  '.task-card',
  '.plan-card',
  '.balance-card',
  '.workflow-card',
  '.mode-button',
  '.choice-card',
  '.resolution-button',
  '.ratio-pill',
  '.upload-card',
  '.history-row',
  '.log-row',
  '.thumb-button',
  '.plan-button',
  '.btn-black',
  '[data-spotlight]'
].join(',')

const FORM_CONTROL_SELECTOR = 'input, textarea, select, option, [contenteditable=""], [contenteditable="true"]'

let revealObserver = null
let motionInstalled = false
let activeSpotlight = null
let spotlightGlow = null
let spotlightFrame = 0
let pendingSpotlight = null
let reducedMotionQuery = null

function prefersReducedMotion() {
  reducedMotionQuery ||= window.matchMedia?.('(prefers-reduced-motion: reduce)')
  return Boolean(reducedMotionQuery?.matches)
}

function ensureRevealObserver() {
  if (revealObserver || prefersReducedMotion()) return revealObserver
  revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('is-revealed')
        revealObserver.unobserve(entry.target)
      })
    },
    {
      threshold: 0.14,
      rootMargin: '0px 0px -8% 0px'
    }
  )
  return revealObserver
}

function normalizeRevealOptions(value) {
  if (typeof value === 'number') return { delay: value }
  return value && typeof value === 'object' ? value : {}
}

function mountReveal(el, binding) {
  const options = normalizeRevealOptions(binding.value)
  el.classList.add('motion-reveal')
  if (Number.isFinite(options.delay)) {
    el.style.setProperty('--reveal-delay', `${options.delay}ms`)
  }
  if (prefersReducedMotion()) {
    el.classList.add('is-revealed')
    return
  }
  ensureRevealObserver()?.observe(el)
}

function unmountReveal(el) {
  revealObserver?.unobserve(el)
}

function handleGlobalRipple(event) {
  if (event.button && event.button !== 0) return
  const target = event.target?.closest?.(RIPPLE_SELECTOR)
  if (!target || target.dataset.ripple === 'off') return
  if (target.matches(FORM_CONTROL_SELECTOR)) return
  if (target.closest('[data-ripple-root="off"]')) return
  if (target.hasAttribute('disabled') || target.getAttribute('aria-disabled') === 'true') return

  const rect = target.getBoundingClientRect()
  if (!rect.width || !rect.height) return

  target.classList.add('motion-ripple-host')
  const ripple = document.createElement('span')
  const size = Math.max(rect.width, rect.height) * 1.35

  ripple.className = 'motion-ripple'
  ripple.style.width = `${size}px`
  ripple.style.height = `${size}px`
  ripple.style.left = `${event.clientX - rect.left - size / 2}px`
  ripple.style.top = `${event.clientY - rect.top - size / 2}px`

  target.appendChild(ripple)
  ripple.addEventListener('animationend', () => ripple.remove(), { once: true })
}

function ensureSpotlightGlow(target) {
  if (!spotlightGlow) {
    spotlightGlow = document.createElement('span')
    spotlightGlow.className = 'motion-spotlight-glow'
    spotlightGlow.setAttribute('aria-hidden', 'true')
  }
  if (spotlightGlow.parentElement !== target) {
    target.appendChild(spotlightGlow)
  }
  return spotlightGlow
}

function clearSpotlight() {
  if (!activeSpotlight) return
  activeSpotlight.classList.remove('motion-spotlight-host', 'is-spotlight-active')
  activeSpotlight = null
  pendingSpotlight = null
  spotlightGlow?.remove()
}

function handleGlobalSpotlight(event) {
  if (prefersReducedMotion()) return

  const target = event.target?.closest?.(SPOTLIGHT_SELECTOR)
  if (!target || target.dataset.spotlight === 'off' || target.matches(FORM_CONTROL_SELECTOR)) {
    clearSpotlight()
    return
  }
  if (target.hasAttribute('disabled') || target.getAttribute('aria-disabled') === 'true') {
    clearSpotlight()
    return
  }

  const rect = target.getBoundingClientRect()
  if (!rect.width || !rect.height) {
    clearSpotlight()
    return
  }

  pendingSpotlight = {
    target,
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
    size: Math.min(260, Math.max(96, Math.max(rect.width, rect.height) * 1.34))
  }

  // 指针移动频率很高，只在下一帧写入样式，避免列表或大卡片 hover 时抖动。
  if (!spotlightFrame) {
    spotlightFrame = requestAnimationFrame(applySpotlight)
  }
}

function applySpotlight() {
  spotlightFrame = 0
  if (!pendingSpotlight) return

  const { target, x, y, size } = pendingSpotlight
  if (activeSpotlight && activeSpotlight !== target) {
    activeSpotlight.classList.remove('motion-spotlight-host', 'is-spotlight-active')
  }

  activeSpotlight = target
  activeSpotlight.classList.add('motion-spotlight-host', 'is-spotlight-active')

  const glow = ensureSpotlightGlow(activeSpotlight)
  glow.style.width = `${size}px`
  glow.style.height = `${size}px`
  glow.style.left = `${x}px`
  glow.style.top = `${y}px`
}

export function installMotion(app) {
  app.directive('reveal', {
    mounted: mountReveal,
    beforeUnmount: unmountReveal
  })

  if (motionInstalled || typeof document === 'undefined') return
  motionInstalled = true
  document.documentElement.classList.add('motion-ready')
  document.addEventListener('pointerdown', handleGlobalRipple, { passive: true, capture: true })
  document.addEventListener('pointermove', handleGlobalSpotlight, { passive: true, capture: true })
  document.addEventListener('pointerleave', clearSpotlight, { passive: true })
  window.addEventListener('blur', clearSpotlight)
}
