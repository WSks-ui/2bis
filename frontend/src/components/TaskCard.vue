<template>
  <div :class="['task-card', `task-card--${task.status}`]" @click="handleClick">
    <div v-if="task.status === 'done' && task.imageUrl" class="task-image-wrap">
      <img :src="task.imageUrl" :alt="task.prompt" class="task-image" loading="lazy" />
      <div class="task-image-actions">
        <button class="task-action-btn" @click.stop="downloadImage" title="下载">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </button>
        <button class="task-action-btn" @click.stop="$emit('remove', task.id)" title="删除">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>

    <div v-else class="task-pending">
      <div class="task-pending-inner">
        <div v-if="task.refPreview" class="task-ref-thumb">
          <img :src="task.refPreview" alt="参考图" />
        </div>

        <div class="task-status-area">
          <div v-if="task.status === 'generating'" class="task-developing">
            <div class="develop-dot"></div>
            <span class="develop-text">生成中…</span>
          </div>
          <div v-else-if="task.status === 'queued'" class="task-queued">
            <div class="queue-dot"></div>
            <span class="queue-text">排队中</span>
          </div>
          <div v-else-if="task.status === 'failed'" class="task-failed-state">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span class="failed-text">{{ task.error }}</span>
          </div>

          <p class="task-prompt-preview">{{ task.prompt }}</p>
        </div>
      </div>

      <div v-if="task.status === 'generating'" class="task-scanline"></div>
    </div>

    <div class="task-meta">
      <span class="task-meta-tag">{{ modeLabel }}</span>
      <span class="task-meta-tag meta-quality">{{ task.quality === 'high' ? '4K' : task.quality === 'medium' ? '中' : '低' }}</span>
      <span class="task-meta-tag meta-size">{{ task.size.replace('x', '×') }}</span>
      <button v-if="task.status === 'failed'" class="task-remove-btn" @click.stop="$emit('remove', task.id)">✕</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: { type: Object, required: true },
})

defineEmits(['remove'])

const modeLabel = computed(() => {
  if (props.task.mode === 'text2img') return '文生图'
  if (props.task.mode === 'ref2img') return '参考图'
  return '编辑'
})

function downloadImage() {
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
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: rgba(232, 230, 220, 0.03);
  border: 1px solid rgba(232, 230, 220, 0.07);
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  animation: card-enter 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
  display: flex;
  flex-direction: column;
  cursor: default;
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.task-card--generating {
  border-color: rgba(217, 119, 87, 0.25);
  box-shadow: 0 0 40px rgba(217, 119, 87, 0.08), inset 0 0 60px rgba(217, 119, 87, 0.02);
}

.task-card--done {
  border-color: rgba(106, 155, 204, 0.18);
  cursor: pointer;
}

.task-card--done:hover {
  border-color: rgba(106, 155, 204, 0.35);
  box-shadow: 0 4px 24px rgba(106, 155, 204, 0.12);
  transform: translateY(-2px);
}

.task-card--failed {
  border-color: rgba(217, 87, 87, 0.2);
  background: rgba(217, 87, 87, 0.02);
}

.task-image-wrap {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.3);
}

.task-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
  animation: image-reveal 0.6s ease both;
}

@keyframes image-reveal {
  from {
    opacity: 0;
    filter: blur(10px) saturate(0);
  }
  to {
    opacity: 1;
    filter: blur(0) saturate(1);
  }
}

.task-card--done:hover .task-image {
  transform: scale(1.04);
}

.task-image-actions {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  background: linear-gradient(transparent, rgba(20, 20, 19, 0.7));
  opacity: 0;
  transition: opacity 0.2s ease;
}

.task-card--done:hover .task-image-actions {
  opacity: 1;
}

.task-action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(250, 249, 245, 0.1);
  border: 1px solid rgba(250, 249, 245, 0.15);
  border-radius: var(--radius-sm);
  color: var(--color-light);
  cursor: pointer;
  transition: all var(--transition-fast);
  backdrop-filter: blur(6px);
}

.task-action-btn:hover {
  background: rgba(250, 249, 245, 0.2);
  border-color: rgba(250, 249, 245, 0.3);
}

.task-pending {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
}

.task-pending-inner {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.task-ref-thumb {
  flex-shrink: 0;
  height: 100px;
  border-radius: var(--radius-md);
  overflow: hidden;
  opacity: 0.4;
  border: 1px solid rgba(232, 230, 220, 0.06);
}

.task-ref-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.task-status-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
}

.task-developing,
.task-queued {
  display: flex;
  align-items: center;
  gap: 10px;
}

.develop-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-orange);
  animation: develop-pulse 1.2s ease-in-out infinite;
  box-shadow: 0 0 12px rgba(217, 119, 87, 0.6);
}

@keyframes develop-pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
    box-shadow: 0 0 8px rgba(217, 119, 87, 0.4);
  }
  50% {
    opacity: 0.4;
    transform: scale(1.5);
    box-shadow: 0 0 20px rgba(217, 119, 87, 0.8);
  }
}

.develop-text {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-orange);
  letter-spacing: 0.02em;
}

.queue-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-mid);
  animation: queue-pulse 2s ease-in-out infinite;
}

@keyframes queue-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.8; }
}

.queue-text {
  font-family: var(--font-heading);
  font-size: 13px;
  color: var(--color-mid);
}

.task-failed-state {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #d75959;
}

.failed-text {
  font-family: var(--font-heading);
  font-size: 12px;
  line-height: 1.5;
  color: #d75959;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.task-prompt-preview {
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-mid);
  opacity: 0.7;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-style: italic;
}

.task-scanline {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(217, 119, 87, 0.015) 2px,
    rgba(217, 119, 87, 0.015) 4px
  );
  animation: scanline-move 3s linear infinite;
  pointer-events: none;
}

@keyframes scanline-move {
  from { transform: translateY(0); }
  to { transform: translateY(4px); }
}

.task-meta {
  padding: 10px 14px;
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
  border-top: 1px solid rgba(232, 230, 220, 0.05);
}

.task-meta-tag {
  font-family: var(--font-heading);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 3px 8px;
  border-radius: 4px;
  background: rgba(232, 230, 220, 0.05);
  color: var(--color-mid);
}

.meta-quality {
  background: rgba(217, 119, 87, 0.08);
  color: var(--color-orange);
}

.meta-size {
  background: rgba(106, 155, 204, 0.08);
  color: var(--color-blue);
}

.task-remove-btn {
  margin-left: auto;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--color-mid);
  cursor: pointer;
  font-size: 12px;
  border-radius: 4px;
  transition: all var(--transition-fast);
}

.task-remove-btn:hover {
  color: #d75959;
  background: rgba(217, 87, 87, 0.08);
}
</style>
