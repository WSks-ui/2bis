<template>
  <article :class="['task-card', `task-card--${task.status}`]">
    <div v-if="task.status === 'done' && task.imageUrl" class="task-image-wrap">
      <img :src="task.imageUrl" :alt="task.prompt" class="task-image" loading="lazy" decoding="async" />
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
        <strong>{{ statusLabel }}</strong>
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
    failed: '已退款'
  }
  return map[props.task.status] || props.task.status
})

const taskDisplayText = computed(() => {
  if (props.task.error) return props.task.error
  return props.task.prompt
})

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
  overflow: hidden;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-line);
  background: rgba(255, 255, 255, 0.74);
  box-shadow: var(--shadow-sm);
  content-visibility: auto;
  contain-intrinsic-size: 360px 460px;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
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
}

.task-image-actions {
  position: absolute;
  right: 10px;
  bottom: 10px;
  display: flex;
  gap: 6px;
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
}

.task-pending {
  padding: 18px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 14px;
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
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-blue);
  font-family: var(--font-ui);
}

.task-progress-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--color-blue);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 700;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 14px currentColor;
}

.task-pending p {
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
  padding: 10px;
  border-top: 1px solid rgba(226, 229, 223, 0.72);
}

.task-meta span {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-paper-soft);
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 700;
}

.task-remove-btn {
  margin-left: auto;
  padding: 5px 9px;
  color: var(--color-red);
}

.task-card--failed .task-state {
  color: var(--color-red);
}

.task-card--done .task-meta span:first-child {
  color: var(--color-green);
}
</style>
