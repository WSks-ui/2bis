const RIPPLE_SELECTOR = [
  'button:not(:disabled)',
  'a[href]',
  '[role="button"]:not([aria-disabled="true"])',
  '[data-ripple]'
].join(',')

const FORM_CONTROL_SELECTOR = 'input, textarea, select, option, [contenteditable=""], [contenteditable="true"]'

let revealObserver = null
let motionInstalled = false

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
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

export function installMotion(app) {
  app.directive('reveal', {
    mounted: mountReveal,
    beforeUnmount: unmountReveal
  })

  if (motionInstalled || typeof document === 'undefined') return
  motionInstalled = true
  document.documentElement.classList.add('motion-ready')
  document.addEventListener('pointerdown', handleGlobalRipple, { passive: true, capture: true })
}
