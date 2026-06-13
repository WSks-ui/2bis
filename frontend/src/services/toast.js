const TYPE_CONFIG = {
  success: { label: '成功', duration: 2400 },
  error: { label: '错误', duration: 3600 },
  warning: { label: '提醒', duration: 3000 },
  info: { label: '提示', duration: 2600 },
}

const MAX_VISIBLE_TOASTS = 4

let root = null

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
    container.firstElementChild?.remove()
  }
}

function show(type, messageOrOptions) {
  if (typeof document === 'undefined') return { close: () => {} }

  const config = TYPE_CONFIG[type] || TYPE_CONFIG.info
  const { message, duration } = normalizeOptions(messageOrOptions, config.duration)
  if (!message) return { close: () => {} }

  const container = ensureRoot()
  const toast = document.createElement('div')
  toast.className = `app-toast app-toast--${type}`
  toast.setAttribute('role', type === 'error' ? 'alert' : 'status')

  const icon = document.createElement('span')
  icon.className = 'app-toast__icon'
  icon.setAttribute('aria-hidden', 'true')

  const text = document.createElement('span')
  text.className = 'app-toast__message'
  text.textContent = message

  const label = document.createElement('span')
  label.className = 'app-toast__label'
  label.textContent = config.label

  toast.append(icon, label, text)
  container.appendChild(toast)
  trimOverflowToasts(container)

  requestAnimationFrame(() => {
    toast.classList.add('is-visible')
  })

  let timer = window.setTimeout(close, duration)

  function close() {
    window.clearTimeout(timer)
    toast.classList.remove('is-visible')
    window.setTimeout(() => {
      toast.remove()
      if (container.children.length === 0) {
        container.remove()
        root = null
      }
    }, 180)
  }

  toast.addEventListener('click', close, { once: true })
  return { close }
}

export const ElMessage = Object.assign((options) => show('info', options), {
  success: (options) => show('success', options),
  error: (options) => show('error', options),
  warning: (options) => show('warning', options),
  info: (options) => show('info', options),
})
