const TYPE_CONFIG = {
  success: { label: '成功', duration: 2400 },
  error: { label: '错误', duration: 3600 },
  warning: { label: '提醒', duration: 3000 },
  info: { label: '提示', duration: 2600 },
}

const MAX_VISIBLE_TOASTS = 4

let root = null
let toastSeed = 0
const activeToasts = new Map()

function ensureRoot() {
  if (root) return root

  root = document.createElement('div')
  root.className = 'app-toast-root'
  root.setAttribute('aria-live', 'polite')
  root.setAttribute('aria-atomic', 'true')
  document.body.appendChild(root)
  return root
}

function normalizeOptions(messageOrOptions, fallbackDuration) {
  if (typeof messageOrOptions === 'string') {
    return { message: messageOrOptions, duration: fallbackDuration }
  }

  return {
    message: messageOrOptions?.message || '',
    duration: messageOrOptions?.duration ?? fallbackDuration,
  }
}

function trimOverflowToasts(container) {
  while (container.children.length > MAX_VISIBLE_TOASTS) {
    const oldest = container.firstElementChild
    oldest?.__closeToast?.()
    if (oldest?.isConnected) oldest.remove()
  }
}

function show(type, messageOrOptions) {
  if (typeof document === 'undefined') return { close: () => {} }

  const config = TYPE_CONFIG[type] || TYPE_CONFIG.info
  const { message, duration } = normalizeOptions(messageOrOptions, config.duration)
  if (!message) return { close: () => {} }

  const container = ensureRoot()
  const dedupeKey = `${type}:${message}`
  const existing = activeToasts.get(dedupeKey)

  // 高频轮询或重复点击会产生相同提示，合并展示能降低噪音。
  if (existing?.toast?.isConnected) {
    existing.count += 1
    existing.countEl.textContent = `×${existing.count}`
    existing.countEl.hidden = false
    existing.restartTimer()
    existing.toast.classList.add('is-bumped')
    window.setTimeout(() => existing.toast.classList.remove('is-bumped'), 180)
    return { close: existing.close }
  }

  const toast = document.createElement('div')
  const toastId = `app-toast-${++toastSeed}`
  toast.className = `app-toast app-toast--${type}`
  toast.id = toastId
  toast.setAttribute('role', type === 'error' ? 'alert' : 'status')
  toast.setAttribute('tabindex', '0')

  const icon = document.createElement('span')
  icon.className = 'app-toast__icon'
  icon.setAttribute('aria-hidden', 'true')

  const text = document.createElement('span')
  text.className = 'app-toast__message'
  text.textContent = message

  const label = document.createElement('span')
  label.className = 'app-toast__label'
  label.textContent = config.label

  const count = document.createElement('span')
  count.className = 'app-toast__count'
  count.hidden = true

  const closeButton = document.createElement('button')
  closeButton.className = 'app-toast__close'
  closeButton.type = 'button'
  closeButton.setAttribute('aria-label', '关闭提示')
  closeButton.textContent = '×'

  const progress = document.createElement('span')
  progress.className = 'app-toast__progress'
  progress.style.animationDuration = `${Math.max(duration, 1)}ms`
  progress.setAttribute('aria-hidden', 'true')

  toast.append(icon, label, text, count, closeButton, progress)
  container.appendChild(toast)
  trimOverflowToasts(container)

  requestAnimationFrame(() => {
    toast.classList.add('is-visible')
  })

  let timer = 0
  let remaining = duration
  let startedAt = 0
  let closed = false

  function startTimer() {
    if (closed) return
    if (!Number.isFinite(remaining) || remaining <= 0) return
    window.clearTimeout(timer)
    startedAt = Date.now()
    timer = window.setTimeout(close, remaining)
    progress.style.animationPlayState = 'running'
  }

  function pauseTimer() {
    if (closed) return
    window.clearTimeout(timer)
    if (startedAt) {
      remaining = Math.max(0, remaining - (Date.now() - startedAt))
      startedAt = 0
    }
    progress.style.animationPlayState = 'paused'
  }

  function restartTimer() {
    if (closed) return
    window.clearTimeout(timer)
    remaining = duration
    startedAt = 0
    progress.style.animation = 'none'
    void progress.offsetWidth
    progress.style.animation = ''
    progress.style.animationDuration = `${Math.max(duration, 1)}ms`
    startTimer()
  }

  function close() {
    if (closed) return
    closed = true
    window.clearTimeout(timer)
    activeToasts.delete(dedupeKey)
    toast.classList.remove('is-visible')
    window.setTimeout(() => {
      toast.remove()
      if (container.children.length === 0) {
        container.remove()
        root = null
      }
    }, 180)
  }

  startTimer()

  const toastState = {
    toast,
    count: 1,
    countEl: count,
    close,
    restartTimer
  }
  activeToasts.set(dedupeKey, toastState)
  toast.__closeToast = close

  closeButton.addEventListener('click', (event) => {
    event.stopPropagation()
    close()
  })
  toast.addEventListener('mouseenter', pauseTimer)
  toast.addEventListener('mouseleave', startTimer)
  toast.addEventListener('focusin', pauseTimer)
  toast.addEventListener('focusout', startTimer)
  toast.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') close()
  })
  return { close }
}

export const ElMessage = Object.assign((options) => show('info', options), {
  success: (options) => show('success', options),
  error: (options) => show('error', options),
  warning: (options) => show('warning', options),
  info: (options) => show('info', options),
})
