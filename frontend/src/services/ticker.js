import { ref } from 'vue'

const VISIBLE_INTERVAL = 1000
const HIDDEN_INTERVAL = 5000

export const sharedNow = ref(Date.now())

let consumers = 0
let timer = null
let visibilityListening = false

export function acquireTicker() {
  consumers += 1
  ensureVisibilityListener()
  startTimer()
}

export function releaseTicker() {
  consumers = Math.max(0, consumers - 1)
  if (consumers === 0) {
    stopTimer()
    removeVisibilityListener()
  }
}

function startTimer() {
  if (timer || consumers === 0) return
  timer = window.setInterval(() => {
    sharedNow.value = Date.now()
  }, currentInterval())
}

function restartTimer() {
  stopTimer()
  sharedNow.value = Date.now()
  startTimer()
}

function stopTimer() {
  if (!timer) return
  window.clearInterval(timer)
  timer = null
}

function currentInterval() {
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    return HIDDEN_INTERVAL
  }
  return VISIBLE_INTERVAL
}

function ensureVisibilityListener() {
  if (visibilityListening || typeof document === 'undefined') return
  document.addEventListener('visibilitychange', restartTimer)
  visibilityListening = true
}

function removeVisibilityListener() {
  if (!visibilityListening || typeof document === 'undefined') return
  document.removeEventListener('visibilitychange', restartTimer)
  visibilityListening = false
}
