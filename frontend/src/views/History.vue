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
          <div class="card-thumb" @click="openPreview(record)">
            <img :src="record.image_url" :alt="record.prompt" loading="lazy" />
            <span :class="['quality-tag', `quality-${record.quality}`]">
              {{ qualityLabel(record.quality) }}
            </span>
          </div>
          <div class="card-info">
            <p class="card-prompt" @click="openPreview(record)">{{ record.prompt }}</p>
            <div class="card-meta">
              <span class="meta-cost">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
                {{ record.points_cost }} 积分
              </span>
              <div class="meta-right">
                <span class="meta-time">{{ formatTime(record.created_at) }}</span>
                <button class="card-delete-btn" @click.stop="confirmDelete(record)" title="删除">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>

    <div v-if="previewRecord || previewClosing" :class="['preview-overlay', { 'preview-out': previewClosing }]" @click.self="closePreview">
      <div :class="['preview-modal', { 'preview-modal-out': previewClosing }]">
        <button class="preview-close" @click="closePreview" title="关闭">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
        <div class="preview-image-wrap">
          <img :src="(previewRecord || {}).image_url" :alt="(previewRecord || {}).prompt" />
        </div>
        <div class="preview-info" v-if="previewRecord">
          <p class="preview-prompt">{{ previewRecord.prompt }}</p>
          <div class="preview-meta">
            <span class="preview-tag">{{ qualityLabel(previewRecord.quality) }}</span>
            <span class="preview-cost">{{ previewRecord.points_cost }} 积分</span>
            <span class="preview-time">{{ formatTime(previewRecord.created_at) }}</span>
          </div>
          <div class="preview-actions">
            <button class="preview-btn preview-btn-download" @click="downloadImage(previewRecord)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              下载
            </button>
            <button class="preview-btn preview-btn-delete" @click="confirmDelete(previewRecord)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="deleteTarget" class="confirm-overlay" @click.self="cancelDelete">
      <div class="confirm-box">
        <p class="confirm-title">确认删除这条记录？</p>
        <p class="confirm-text">删除后不可恢复，生成图片也会被一并删除</p>
        <div class="confirm-actions">
          <button class="confirm-btn confirm-cancel" @click="cancelDelete">取消</button>
          <button class="confirm-btn confirm-ok" @click="doDelete" :disabled="deleting">
            {{ deleting ? '删除中…' : '确认删除' }}
          </button>
        </div>
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
const previewRecord = ref(null)
const previewClosing = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

onMounted(() => {
  fetchHistory()
})

async function fetchHistory() {
  loading.value = true
  try {
    const res = await api.get('/history')
    records.value = Array.isArray(res.data) ? res.data : (res.data.records || [])
  } catch (e) {
    console.error('Failed to fetch history', e)
  } finally {
    loading.value = false
  }
}

function openPreview(record) {
  previewClosing.value = false
  previewRecord.value = record
}

function closePreview() {
  if (previewClosing.value) return
  previewClosing.value = true
  setTimeout(() => {
    previewRecord.value = null
    previewClosing.value = false
  }, 300)
}

function confirmDelete(record) {
  deleteTarget.value = record
}

function cancelDelete() {
  deleteTarget.value = null
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`/history/${deleteTarget.value.id}`)
    records.value = records.value.filter((r) => r.id !== deleteTarget.value.id)
    if (previewRecord.value && previewRecord.value.id === deleteTarget.value.id) {
      closePreview()
    }
    deleteTarget.value = null
  } catch (e) {
    console.error('Failed to delete history', e)
  } finally {
    deleting.value = false
  }
}

function downloadImage(record) {
  const url = record.image_url
  if (!url) return
  if (url.startsWith('data:')) {
    const a = document.createElement('a')
    a.href = url
    a.download = `2bis-${record.id}.png`
    a.click()
  } else {
    window.open(url, '_blank')
  }
}

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

.meta-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-delete-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--color-mid);
  cursor: pointer;
  opacity: 0.4;
  transition: all 0.2s ease;
}

.history-card:hover .card-delete-btn {
  opacity: 1;
  border-color: rgba(232, 230, 220, 0.12);
}

.card-delete-btn:hover {
  color: #d75959;
  background: rgba(217, 87, 87, 0.1);
  border-color: rgba(217, 87, 87, 0.2);
}

.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(10, 10, 9, 0.92);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  animation: overlay-in 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.preview-overlay.preview-out {
  animation: overlay-out 0.25s ease forwards;
}

@keyframes overlay-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes overlay-out {
  from { opacity: 1; }
  to { opacity: 0; }
}

.preview-modal {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: rgba(28, 28, 26, 0.95);
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-lg);
  overflow: hidden;
  animation: modal-in 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.preview-modal.preview-modal-out {
  animation: modal-out 0.22s cubic-bezier(0.55, 0, 1, 0.45) forwards;
}

@keyframes modal-in {
  from { opacity: 0; transform: scale(0.95) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

@keyframes modal-out {
  from { opacity: 1; transform: scale(1) translateY(0); }
  to { opacity: 0; transform: scale(0.92) translateY(6px); }
}

.preview-close {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 10;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(232, 230, 220, 0.08);
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: 50%;
  color: var(--color-light);
  cursor: pointer;
  transition: all 0.2s ease;
  backdrop-filter: blur(8px);
}

.preview-close:hover {
  background: rgba(232, 230, 220, 0.16);
  border-color: rgba(232, 230, 220, 0.24);
}

.preview-image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  max-height: 65vh;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.4);
}

.preview-image-wrap img {
  max-width: 100%;
  max-height: 65vh;
  object-fit: contain;
}

.preview-info {
  padding: 20px 24px;
  border-top: 1px solid rgba(232, 230, 220, 0.06);
}

.preview-prompt {
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-light);
  margin-bottom: 14px;
  max-height: 80px;
  overflow-y: auto;
}

.preview-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.preview-tag {
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  background: rgba(217, 119, 87, 0.12);
  color: var(--color-orange);
  border: 1px solid rgba(217, 119, 87, 0.2);
}

.preview-cost {
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-green);
}

.preview-time {
  font-family: var(--font-heading);
  font-size: 12px;
  color: var(--color-mid);
}

.preview-actions {
  display: flex;
  gap: 10px;
}

.preview-btn {
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  border: 1px solid;
}

.preview-btn-download {
  background: rgba(106, 155, 204, 0.1);
  border-color: rgba(106, 155, 204, 0.2);
  color: var(--color-blue);
}

.preview-btn-download:hover {
  background: rgba(106, 155, 204, 0.2);
  border-color: rgba(106, 155, 204, 0.35);
}

.preview-btn-delete {
  background: rgba(217, 87, 87, 0.08);
  border-color: rgba(217, 87, 87, 0.15);
  color: #d75959;
}

.preview-btn-delete:hover {
  background: rgba(217, 87, 87, 0.16);
  border-color: rgba(217, 87, 87, 0.3);
}

.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: rgba(10, 10, 9, 0.7);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: overlay-in 0.2s ease both;
}

.confirm-box {
  background: rgba(28, 28, 26, 0.98);
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-lg);
  padding: 32px;
  max-width: 380px;
  width: 90%;
  text-align: center;
  animation: modal-in 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.confirm-title {
  font-family: var(--font-heading);
  font-size: 17px;
  font-weight: 700;
  color: var(--color-light);
  margin-bottom: 10px;
}

.confirm-text {
  font-size: 14px;
  color: var(--color-mid);
  line-height: 1.6;
  margin-bottom: 24px;
}

.confirm-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.confirm-btn {
  padding: 10px 28px;
  border-radius: var(--radius-sm);
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid;
}

.confirm-cancel {
  background: rgba(232, 230, 220, 0.06);
  border-color: rgba(232, 230, 220, 0.12);
  color: var(--color-mid);
}

.confirm-cancel:hover {
  background: rgba(232, 230, 220, 0.1);
}

.confirm-ok {
  background: rgba(217, 87, 87, 0.15);
  border-color: rgba(217, 87, 87, 0.3);
  color: #f06a6a;
}

.confirm-ok:hover:not(:disabled) {
  background: #d75959;
  color: #fff;
  border-color: #d75959;
}

.confirm-ok:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
