<template>
  <article :class="['task-card', `task-card--${task.status}`]" :aria-label="cardAriaLabel">
    <div class="task-status-badge">
      <span class="status-dot" aria-hidden="true"></span>
      <span>{{ statusLabel }}</span>
    </div>

    <div v-if="task.status === 'done' && task.imageUrl" class="task-image-wrap">
      <img :src="task.imageUrl" :alt="task.prompt" class="task-image" loading="lazy" decoding="async" />
      <div class="task-image-caption">
        <span>{{ modeLabel }}</span>
        <strong>{{ compactPrompt }}</strong>
      </div>
      <div class="task-image-actions">
        <button class="task-action-btn" @click.stop="downloadImage" title="下载">↓</button>
        <button class="task-action-btn" @click.stop="$emit('remove', task.id)" title="删除">×</button>
      </div>
    </div>

    <div v-else class="task-pending">
      <div v-if="referencePreviews.length" class="task-ref-thumb-grid">
        <img
          v-for="(preview, index) in referencePreviews"
          :key="`${preview}-${index}`"
          :src="preview"
          :alt="`参考图 ${index + 1}`"
          loading="lazy"
          decoding="async"
        />
      </div>
      <div class="task-state">
        <span class="status-dot"></span>
        <strong>{{ pendingHeadline }}</strong>
      </div>
      <div v-if="task.progressMessage || timeLabel || task.pollError" class="task-progress-meta">
        <span v-if="task.progressMessage">{{ task.progressMessage }}</span>
        <span v-if="timeLabel">{{ timeLabel }}</span>
        <span v-if="task.pollError">刷新异常：{{ task.pollError }}</span>
      </div>
      <p>{{ taskDisplayText }}</p>
    </div>

    <footer class="task-meta">
      <span>{{ modeLabel }}</span>
      <span>{{ qualityLabel }}</span>
      <span>{{ task.size?.replace('x', '×') }}</span>
      <span v-if="task.workflowType && task.workflowType !== 'standard'">{{ workflowLabel }}</span>
      <span v-if="task.pointsCost">{{ task.pointsCost }} 额度</span>
      <span v-if="task.balanceSource">{{ sourceLabel }}</span>
      <span v-if="task.status === 'done' && timeLabel">{{ timeLabel }}</span>
      <span v-if="upstreamTimingLabel">{{ upstreamTimingLabel }}</span>
      <span v-if="upstreamTransferLabel">{{ upstreamTransferLabel }}</span>
      <span v-if="task.upstreamRequestQuality">请求质量 {{ task.upstreamRequestQuality }}</span>
      <span v-if="task.upstreamRequestId">上游 {{ shortRequestId }}</span>
      <button v-if="task.status === 'failed'" class="task-remove-btn" @click.stop="$emit('remove', task.id)">移除</button>
    </footer>
  </article>
</template>

<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'
import { acquireTicker, releaseTicker, sharedNow } from '../services/ticker'

const props = defineProps({
  task: { type: Object, required: true },
})

defineEmits(['remove'])

let tickerActive = false

watch(
  () => props.task.status,
  (status) => {
    const needsTicker = status === 'queued' || status === 'generating'
    if (needsTicker && !tickerActive) {
      acquireTicker()
      tickerActive = true
    } else if (!needsTicker && tickerActive) {
      releaseTicker()
      tickerActive = false
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  if (tickerActive) {
    releaseTicker()
    tickerActive = false
  }
})

const modeLabel = computed(() => {
  if (props.task.mode === 'text2img') return '文生图'
  if (props.task.mode === 'ref2img') return '参考图'
  return '编辑'
})

const qualityLabel = computed(() => {
  const map = { low: '低质量', medium: '中质量', high: '高质量' }
  return map[props.task.quality] || props.task.quality
})

const statusLabel = computed(() => {
  if (props.task.progressStage === 'receiving') return '接收图片中'
  if (props.task.progressStage === 'saving') return '保存图片中'
  const map = {
    queued: '排队中',
    generating: '生成中',
    done: '已完成',
    failed: '已退款'
  }
  return map[props.task.status] || props.task.status
})

const pendingHeadline = computed(() => {
  if (props.task.status === 'failed') return '生成失败，额度已回退'
  return statusLabel.value
})

const taskDisplayText = computed(() => {
  if (props.task.error) return props.task.error
  return props.task.prompt
})

const compactPrompt = computed(() => {
  const text = taskDisplayText.value || '未命名作品'
  return text.length > 34 ? `${text.slice(0, 34)}…` : text
})

const cardAriaLabel = computed(() => `${statusLabel.value}，${compactPrompt.value}`)

const sourceLabel = computed(() => {
  const map = { free_points: '体验积分', quota: '订阅额度', points: '普通积分' }
  return map[props.task.balanceSource] || '未知来源'
})

const workflowLabel = computed(() => {
  const map = { professional: '专业工作流' }
  return map[props.task.workflowType] || props.task.workflowType
})

const referencePreviews = computed(() => {
  if (Array.isArray(props.task.refPreviews) && props.task.refPreviews.length) {
    return props.task.refPreviews.slice(0, 3)
  }
  return props.task.refPreview ? [props.task.refPreview] : []
})

const upstreamTimingLabel = computed(() => {
  if (!props.task.upstreamElapsedSeconds) return ''
  const parts = [`上游 ${formatSeconds(props.task.upstreamElapsedSeconds)}`]
  if (props.task.upstreamHeaderSeconds != null) parts.push(`等待 ${formatSeconds(props.task.upstreamHeaderSeconds)}`)
  if (props.task.upstreamBodySeconds != null) parts.push(`接收 ${formatSeconds(props.task.upstreamBodySeconds)}`)
  if (props.task.upstreamSaveSeconds != null) parts.push(`保存 ${formatSeconds(props.task.upstreamSaveSeconds)}`)
  return parts.join(' / ')
})

const upstreamTransferLabel = computed(() => {
  if (!props.task.upstreamBodyBytes) return ''
  const transfer = props.task.upstreamTransferEncoding ? ` · ${props.task.upstreamTransferEncoding}` : ''
  const total = props.task.upstreamContentLength ? ` / ${formatBytes(props.task.upstreamContentLength)}` : ''
  return `传输 ${formatBytes(props.task.upstreamBodyBytes)}${total}${transfer}`
})

const timeLabel = computed(() => {
  const createdAt = parseDate(props.task.createdAt)
  if (!createdAt) return ''

  const finishedAt = parseDate(props.task.finishedAt)
  if (finishedAt) {
    return `耗时 ${formatDuration(finishedAt - createdAt)}`
  }

  if (props.task.status === 'queued' || props.task.status === 'generating') {
    return `已等待 ${formatDuration(sharedNow.value - createdAt)}`
  }

  return ''
})

const shortRequestId = computed(() => {
  const value = props.task.upstreamRequestId || ''
  if (value.length <= 14) return value
  return `${value.slice(0, 8)}…${value.slice(-4)}`
})

function parseDate(value) {
  if (!value) return null
  const normalized = String(value).includes('T') ? String(value) : `${String(value).replace(' ', 'T')}Z`
  const date = new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(normalized) ? normalized : `${normalized}Z`)
  if (Number.isNaN(date.getTime())) return null
  return date.getTime()
}

function formatDuration(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const restMinutes = minutes % 60
    return `${hours}小时${restMinutes}分`
  }
  if (minutes > 0) return `${minutes}分${seconds}秒`
  return `${seconds}秒`
}

function formatSeconds(seconds) {
  if (!Number.isFinite(seconds)) return ''
  if (seconds < 10) return `${seconds.toFixed(1)}s`
  return `${Math.round(seconds)}s`
}

function formatBytes(value) {
  const size = Number(value) || 0
  if (size < 1024) return `${size}B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}KB`
  return `${(size / 1024 / 1024).toFixed(1)}MB`
}

function downloadImage() {
  if (!props.task.imageUrl) return
  const a = document.createElement('a')
  a.href = props.task.imageUrl
  a.download = `2bis-${props.task.id}.png`
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>

<style scoped>
.task-card {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-line);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(250, 250, 246, 0.72)),
    rgba(255, 255, 255, 0.74);
  box-shadow: var(--shadow-sm);
  content-visibility: auto;
  contain-intrinsic-size: 360px 460px;
  transform: translateZ(0);
  isolation: isolate;
  transition:
    border-color var(--transition-base),
    transform var(--transition-base),
    box-shadow var(--transition-base),
    filter var(--transition-base);
}

.task-card:hover {
  border-color: rgba(60, 110, 232, 0.22);
  transform: translateY(-4px) scale(1.01);
  box-shadow: var(--shadow-md);
}

.task-card::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  background: linear-gradient(130deg, rgba(255, 255, 255, 0.34), transparent 32%);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.task-card:hover::after {
  opacity: 1;
}

.task-status-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 3;
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 11px;
  border: 1px solid rgba(255, 255, 255, 0.52);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 12px 28px rgba(23, 23, 23, 0.1);
  color: var(--color-green);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 900;
  backdrop-filter: blur(14px);
  opacity: 0;
  transform: translate3d(0, -8px, 0);
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.task-card:hover .task-status-badge,
.task-card--queued .task-status-badge,
.task-card--generating .task-status-badge,
.task-card--failed .task-status-badge {
  opacity: 1;
  transform: translate3d(0, 0, 0);
}

.task-image-wrap,
.task-pending {
  position: relative;
  aspect-ratio: 1;
  background:
    linear-gradient(135deg, rgba(23, 23, 23, 0.04), rgba(23, 23, 23, 0.015)),
    var(--color-paper-soft);
}

.task-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  opacity: 0;
  transform: scale(1.02);
  animation: task-image-in 520ms var(--ease-out-soft) forwards;
  transition: transform 520ms var(--ease-out-soft), filter var(--transition-base);
}

.task-card:hover .task-image {
  transform: scale(1.055);
  filter: saturate(1.04) contrast(1.02);
}

.task-image-actions {
  position: absolute;
  z-index: 3;
  right: 10px;
  bottom: 10px;
  display: flex;
  gap: 6px;
  opacity: 0;
  transform: translate3d(0, 8px, 0);
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.task-image-caption {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 12px;
  z-index: 2;
  display: grid;
  gap: 3px;
  padding: 13px 72px 13px 14px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: var(--radius-md);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.22), rgba(23, 23, 23, 0.3)),
    rgba(23, 23, 23, 0.28);
  color: #fff;
  opacity: 0;
  transform: translate3d(0, 10px, 0);
  backdrop-filter: blur(16px);
  transition:
    opacity var(--transition-base),
    transform var(--transition-base),
    background var(--transition-base);
}

.task-image-caption span {
  font-family: var(--font-ui);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  opacity: 0.76;
}

.task-image-caption strong {
  min-width: 0;
  overflow: hidden;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card:hover .task-image-caption {
  opacity: 1;
  transform: translate3d(0, 0, 0);
}

.task-card:hover .task-image-actions {
  opacity: 1;
  transform: translate3d(0, 0, 0);
}

.task-action-btn,
.task-remove-btn {
  border: 1px solid rgba(255, 255, 255, 0.58);
  background: rgba(255, 255, 255, 0.78);
  color: var(--color-ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: var(--font-heading);
  font-weight: 800;
  backdrop-filter: blur(10px);
}

.task-action-btn {
  width: 32px;
  height: 32px;
  transition: transform var(--transition-base), background var(--transition-base), box-shadow var(--transition-base);
}

.task-action-btn:hover,
.task-remove-btn:hover {
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 10px 20px rgba(23, 23, 23, 0.12);
  transform: translateY(-1px);
}

.task-action-btn:active,
.task-remove-btn:active {
  transform: translateY(0) scale(0.96);
}

.task-pending {
  padding: 18px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 14px;
  overflow: hidden;
}

.task-pending::after {
  content: '';
  position: absolute;
  inset: auto -20% -28% -20%;
  height: 58%;
  pointer-events: none;
  background: radial-gradient(ellipse at 50% 100%, rgba(60, 110, 232, 0.13), transparent 68%);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.task-card--queued .task-pending::after,
.task-card--generating .task-pending::after {
  opacity: 1;
}

.task-ref-thumb-grid {
  height: 96px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  opacity: 0.64;
}

.task-ref-thumb-grid img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  overflow: hidden;
  border-radius: var(--radius-sm);
}

.task-state {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-blue);
  font-family: var(--font-ui);
}

.task-progress-meta {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--color-blue);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 700;
}

.task-progress-meta span {
  padding: 4px 7px;
  border: 1px solid rgba(60, 110, 232, 0.13);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.56);
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 14px currentColor;
  animation: task-dot 1.2s ease-in-out infinite;
}

.task-pending p {
  position: relative;
  z-index: 1;
  color: var(--color-muted);
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 11px;
  border-top: 1px solid rgba(226, 229, 223, 0.72);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.34), rgba(245, 246, 241, 0.48)),
    rgba(255, 255, 255, 0.26);
}

.task-meta span {
  padding: 5px 8px;
  border: 1px solid rgba(226, 229, 223, 0.82);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.56);
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 700;
  transition: color var(--transition-base), border-color var(--transition-base), background var(--transition-base);
}

.task-card:hover .task-meta span {
  border-color: rgba(207, 212, 203, 0.9);
  background: rgba(255, 255, 255, 0.72);
}

.task-remove-btn {
  margin-left: auto;
  padding: 5px 9px;
  color: var(--color-red);
}

.task-card--failed .task-state {
  color: var(--color-red);
}

.task-card--failed .task-pending {
  background:
    linear-gradient(135deg, rgba(200, 77, 60, 0.08), rgba(255, 255, 255, 0.34)),
    var(--color-paper-soft);
}

.task-card--failed .task-progress-meta span {
  border-color: rgba(200, 77, 60, 0.16);
  color: var(--color-red);
}

.task-card--failed .task-status-badge {
  color: var(--color-red);
}

.task-card--queued .task-status-badge,
.task-card--generating .task-status-badge {
  color: var(--color-blue);
}

.task-card--done .task-meta span:first-child {
  color: var(--color-green);
  border-color: rgba(63, 140, 104, 0.22);
  background: rgba(63, 140, 104, 0.08);
}

.task-card--done .status-dot,
.task-card--failed .status-dot {
  animation: none;
}

.task-card--generating .task-pending::before,
.task-card--queued .task-pending::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, 0.64) 46%, transparent 62%),
    transparent;
  transform: translateX(-120%);
  animation: pending-sheen 2.1s ease-in-out infinite;
}

@media (max-width: 640px) {
  .task-status-badge {
    top: 10px;
    left: 10px;
    opacity: 1;
    transform: none;
  }

  .task-image-caption {
    left: 10px;
    right: 10px;
    bottom: 10px;
    padding-right: 68px;
    opacity: 1;
    transform: none;
  }

  .task-image-actions {
    opacity: 1;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .task-card,
  .task-card:hover,
  .task-card:hover .task-image,
  .task-card:hover .task-image-caption {
    transform: none;
  }

  .status-dot,
  .task-card--generating .task-pending::before,
  .task-card--queued .task-pending::before {
    animation: none;
  }
}

@keyframes task-image-in {
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes task-dot {
  0%, 100% {
    opacity: 0.55;
    transform: scale(1);
  }

  50% {
    opacity: 1;
    transform: scale(1.55);
  }
}

@keyframes pending-sheen {
  0% {
    transform: translateX(-120%);
  }

  52%, 100% {
    transform: translateX(120%);
  }
}
</style>
