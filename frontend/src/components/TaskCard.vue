<template>
  <article :class="['task-card', `task-card--${task.status}`]">
    <div v-if="task.status === 'done' && task.imageUrl" class="task-image-wrap">
      <img :src="task.imageUrl" :alt="task.prompt" class="task-image" loading="lazy" />
      <div class="task-image-actions">
        <button class="task-action-btn" @click.stop="downloadImage" title="下载">↓</button>
        <button class="task-action-btn" @click.stop="$emit('remove', task.id)" title="删除">×</button>
      </div>
    </div>

    <div v-else class="task-pending">
      <div v-if="task.refPreview" class="task-ref-thumb">
        <img :src="task.refPreview" alt="参考图" />
      </div>
      <div class="task-state">
        <span class="status-dot"></span>
        <strong>{{ statusLabel }}</strong>
      </div>
      <div v-if="timeLabel || task.pollError" class="task-progress-meta">
        <span v-if="timeLabel">{{ timeLabel }}</span>
        <span v-if="task.pollError">刷新异常：{{ task.pollError }}</span>
      </div>
      <p>{{ task.error || task.prompt }}</p>
    </div>

    <footer class="task-meta">
      <span>{{ modeLabel }}</span>
      <span>{{ qualityLabel }}</span>
      <span>{{ task.size?.replace('x', '×') }}</span>
      <span v-if="task.workflowType && task.workflowType !== 'standard'">{{ workflowLabel }}</span>
      <span v-if="task.pointsCost">{{ task.pointsCost }} 额度</span>
      <span v-if="task.balanceSource">{{ sourceLabel }}</span>
      <span v-if="task.status === 'done' && timeLabel">{{ timeLabel }}</span>
      <span v-if="task.upstreamRequestQuality">请求质量 {{ task.upstreamRequestQuality }}</span>
      <span v-if="task.upstreamRequestId">上游 {{ shortRequestId }}</span>
      <button v-if="task.status === 'failed'" class="task-remove-btn" @click.stop="$emit('remove', task.id)">移除</button>
    </footer>
  </article>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  task: { type: Object, required: true },
})

defineEmits(['remove'])

const now = ref(Date.now())
const timer = window.setInterval(() => {
  now.value = Date.now()
}, 1000)

onBeforeUnmount(() => {
  window.clearInterval(timer)
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
  const map = {
    queued: '排队中',
    generating: '生成中',
    failed: '已退款'
  }
  return map[props.task.status] || props.task.status
})

const sourceLabel = computed(() => {
  const map = { free_points: '体验积分', quota: '订阅额度', points: '普通积分' }
  return map[props.task.balanceSource] || '未知来源'
})

const workflowLabel = computed(() => {
  const map = { professional: '专业工作流' }
  return map[props.task.workflowType] || props.task.workflowType
})

const timeLabel = computed(() => {
  const createdAt = parseDate(props.task.createdAt)
  if (!createdAt) return ''

  const finishedAt = parseDate(props.task.finishedAt)
  if (finishedAt) {
    return `耗时 ${formatDuration(finishedAt - createdAt)}`
  }

  if (props.task.status === 'queued' || props.task.status === 'generating') {
    return `已等待 ${formatDuration(now.value - createdAt)}`
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
  const date = new Date(value)
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

.task-ref-thumb {
  height: 96px;
  overflow: hidden;
  border-radius: var(--radius-md);
  opacity: 0.64;
}

.task-ref-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
