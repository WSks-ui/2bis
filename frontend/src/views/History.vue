<template>
  <div class="history-page">
    <NavBar />

    <div class="page-container">
      <div class="section-header">
        <h2 class="page-title">
          <span class="title-accent"></span>
          生成历史
        </h2>
        <p class="page-desc">你所有 AI 生成的图片记录</p>
      </div>

      <div v-if="loading" class="loading-area">
        <div v-for="n in 4" :key="n" class="skeleton-card">
          <div class="skeleton-thumb"></div>
          <div class="skeleton-content">
            <div class="skeleton-line skeleton-line--long"></div>
            <div class="skeleton-line skeleton-line--short"></div>
          </div>
        </div>
      </div>

      <div v-else-if="!records.length" class="empty-area">
        <svg class="empty-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
        <p class="empty-text">暂无生成记录</p>
        <p class="empty-hint">去首页开始你的第一次 AI 创作吧</p>
        <router-link to="/" class="btn-empty-action">开始创作</router-link>
      </div>

      <div v-else class="history-grid">
        <article
          v-for="record in records"
          :key="record.id"
          class="history-card"
        >
          <div class="card-thumb">
            <img :src="record.image_url" :alt="record.prompt" loading="lazy" />
            <span :class="['quality-tag', `quality-${record.quality}`]">
              {{ qualityLabel(record.quality) }}
            </span>
          </div>
          <div class="card-info">
            <p class="card-prompt">{{ record.prompt }}</p>
            <div class="card-meta">
              <span class="meta-cost">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
                {{ record.points_cost }} 积分
              </span>
              <span class="meta-time">{{ formatTime(record.created_at) }}</span>
            </div>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
import NavBar from '../components/NavBar.vue'

const records = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/history')
    records.value = res.data.records || res.data || []
  } catch (e) {
    console.error('Failed to fetch history', e)
  } finally {
    loading.value = false
  }
})

function qualityLabel(quality) {
  const map = { low: '低质量', medium: '中等', high: '高质量' }
  return map[quality] || quality
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}
</script>

<style scoped>
.history-page {
  min-height: 100vh;
  background: var(--color-dark);
}

.page-container {
  max-width: 1024px;
  margin: 0 auto;
  padding: 48px 24px 80px;
  animation: page-enter 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

@keyframes page-enter {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-header {
  margin-bottom: 36px;
}

.page-title {
  font-size: 26px;
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 10px;
}

.title-accent {
  width: 4px;
  height: 26px;
  border-radius: 2px;
  background: var(--color-orange);
  display: inline-block;
}

.page-desc {
  font-size: 15px;
  color: var(--color-mid);
  margin-left: 18px;
  font-style: italic;
}

.loading-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-card {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: rgba(232, 230, 220, 0.03);
  border-radius: var(--radius-md);
}

.skeleton-thumb {
  width: 100px;
  height: 70px;
  border-radius: var(--radius-sm);
  background: rgba(232, 230, 220, 0.06);
  animation: shimmer 1.5s infinite;
}

.skeleton-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
}

.skeleton-line {
  height: 12px;
  border-radius: 4px;
  background: rgba(232, 230, 220, 0.06);
  animation: shimmer 1.5s infinite;
}

.skeleton-line--long {
  width: 80%;
}

.skeleton-line--short {
  width: 40%;
}

@keyframes shimmer {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.empty-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 20px;
  text-align: center;
  animation: empty-enter 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.2s both;
}

@keyframes empty-enter {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.empty-icon {
  color: var(--color-mid);
  opacity: 0.4;
  margin-bottom: 24px;
}

.empty-text {
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 600;
  color: var(--color-mid);
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 14px;
  color: var(--color-mid);
  opacity: 0.7;
  margin-bottom: 24px;
}

.btn-empty-action {
  padding: 10px 28px;
  background: rgba(217, 119, 87, 0.12);
  border: 1px solid rgba(217, 119, 87, 0.25);
  border-radius: var(--radius-md);
  color: var(--color-orange);
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: all var(--transition-base);
}

.btn-empty-action:hover {
  background: var(--color-orange);
  color: var(--color-dark);
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.history-card {
  background: rgba(232, 230, 220, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.08);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  animation: card-rise 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.history-card:nth-child(1) { animation-delay: 0.1s; }
.history-card:nth-child(2) { animation-delay: 0.15s; }
.history-card:nth-child(3) { animation-delay: 0.2s; }
.history-card:nth-child(4) { animation-delay: 0.25s; }
.history-card:nth-child(n+5) { animation-delay: 0.3s; }

@keyframes card-rise {
  from { opacity: 0; transform: translateY(24px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.history-card:hover {
  transform: translateY(-2px);
  border-color: rgba(232, 230, 220, 0.16);
  box-shadow: var(--shadow-md);
}

.card-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
}

.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--transition-slow);
}

.history-card:hover .card-thumb img {
  transform: scale(1.05);
}

.quality-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 10px;
  border-radius: 20px;
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 600;
  backdrop-filter: blur(8px);
}

.quality-low {
  background: rgba(120, 140, 93, 0.2);
  color: var(--color-green);
  border: 1px solid rgba(120, 140, 93, 0.3);
}

.quality-medium {
  background: rgba(106, 155, 204, 0.2);
  color: var(--color-blue);
  border: 1px solid rgba(106, 155, 204, 0.3);
}

.quality-high {
  background: rgba(217, 119, 87, 0.2);
  color: var(--color-orange);
  border: 1px solid rgba(217, 119, 87, 0.3);
}

.card-info {
  padding: 18px;
}

.card-prompt {
  font-size: 14px;
  color: var(--color-light);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 14px;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-cost {
  display: flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-green);
}

.meta-time {
  font-family: var(--font-heading);
  font-size: 12px;
  color: var(--color-mid);
}

@media (max-width: 640px) {
  .history-grid {
    grid-template-columns: 1fr;
  }

  .page-title {
    font-size: 22px;
  }
}
</style>
