<template>
  <div class="history-page">
    <NavBar />

    <main class="page-container">
      <header class="page-header">
        <h1>生成历史</h1>
        <p>查看已完成的创作记录、消费额度和扣费来源。</p>
      </header>

      <div v-if="loading" class="state-area">加载中...</div>

      <div v-else-if="!records.length" class="state-area">
        <p>暂无生成记录</p>
        <router-link to="/" class="btn-primary">开始创作</router-link>
      </div>

      <section v-else class="history-grid">
        <article v-for="record in records" :key="record.id" class="history-card">
          <button class="thumb-button" @click="openPreview(record)">
            <img :src="record.image_url" :alt="record.prompt" loading="lazy" />
            <span :class="['quality-tag', `quality-${record.quality}`]">
              {{ qualityLabel(record.quality) }}
            </span>
          </button>
          <div class="card-info">
            <p class="prompt-text">{{ record.prompt }}</p>
            <div class="meta-row">
              <span>{{ record.points_cost }} 额度</span>
              <span>{{ sourceLabel(record.balance_source) }}</span>
              <span v-if="record.workflow_type && record.workflow_type !== 'standard'">
                {{ workflowLabel(record.workflow_type) }}
              </span>
              <span>{{ formatTime(record.created_at) }}</span>
            </div>
            <div class="card-actions">
              <button class="btn-ghost" @click="downloadImage(record)">下载</button>
              <button class="btn-danger" @click="confirmDelete(record)">删除</button>
            </div>
          </div>
        </article>
      </section>
    </main>

    <div v-if="previewRecord" class="preview-overlay" @click.self="closePreview">
      <div class="preview-modal">
        <button class="preview-close" @click="closePreview">×</button>
        <img :src="previewRecord.image_url" :alt="previewRecord.prompt" />
        <div class="preview-info">
          <p>{{ previewRecord.prompt }}</p>
          <div class="meta-row">
            <span>{{ qualityLabel(previewRecord.quality) }}</span>
            <span>{{ previewRecord.points_cost }} 额度</span>
            <span>{{ sourceLabel(previewRecord.balance_source) }}</span>
            <span v-if="previewRecord.workflow_type && previewRecord.workflow_type !== 'standard'">
              {{ workflowLabel(previewRecord.workflow_type) }}
            </span>
            <span>{{ formatTime(previewRecord.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="deleteTarget" class="confirm-overlay" @click.self="cancelDelete">
      <div class="confirm-box">
        <h3>确认删除这条记录？</h3>
        <p>删除后不会恢复，生成图片文件也会一并删除。</p>
        <div class="confirm-actions">
          <button class="btn-ghost" @click="cancelDelete">取消</button>
          <button class="btn-danger" :disabled="deleting" @click="doDelete">
            {{ deleting ? '删除中' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'
import NavBar from '../components/NavBar.vue'

const records = ref([])
const loading = ref(true)
const previewRecord = ref(null)
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
  previewRecord.value = record
}

function closePreview() {
  previewRecord.value = null
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
    records.value = records.value.filter((record) => record.id !== deleteTarget.value.id)
    if (previewRecord.value?.id === deleteTarget.value.id) closePreview()
    deleteTarget.value = null
  } catch (e) {
    console.error('Failed to delete history', e)
  } finally {
    deleting.value = false
  }
}

function downloadImage(record) {
  if (!record.image_url) return
  const a = document.createElement('a')
  a.href = record.image_url
  a.download = `2bis-${record.id}.png`
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function qualityLabel(quality) {
  const map = { low: '低质量', medium: '中质量', high: '高质量' }
  return map[quality] || quality
}

function sourceLabel(source) {
  const map = { free_points: '体验积分', quota: '订阅额度', points: '普通积分' }
  return map[source] || '未知来源'
}

function workflowLabel(type) {
  const map = { professional: '专业工作流' }
  return map[type] || type
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
  max-width: 1120px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  margin: 0;
  color: var(--color-light);
  font-family: var(--font-heading);
  font-size: 34px;
}

.page-header p,
.state-area,
.prompt-text,
.meta-row,
.confirm-box p {
  color: var(--color-mid);
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.history-card,
.confirm-box,
.preview-modal {
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-lg);
  background: rgba(232, 230, 220, 0.04);
}

.thumb-button {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  padding: 0;
  border: 0;
  background: rgba(0, 0, 0, 0.25);
  cursor: pointer;
  overflow: hidden;
}

.thumb-button img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.quality-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 10px;
  border-radius: 16px;
  background: rgba(20, 20, 19, 0.72);
  color: var(--color-light);
  font-size: 12px;
  font-weight: 700;
}

.card-info {
  padding: 18px;
}

.prompt-text {
  min-height: 44px;
  line-height: 1.6;
  margin: 0 0 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  font-size: 12px;
  font-family: var(--font-heading);
}

.card-actions,
.confirm-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.btn-primary,
.btn-ghost,
.btn-danger {
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 9px 16px;
  cursor: pointer;
  font-family: var(--font-heading);
  font-weight: 700;
  text-decoration: none;
}

.btn-primary {
  background: var(--color-orange);
  color: var(--color-dark);
}

.btn-ghost {
  background: transparent;
  border-color: rgba(232, 230, 220, 0.14);
  color: var(--color-mid);
}

.btn-danger {
  background: rgba(217, 87, 87, 0.12);
  border-color: rgba(217, 87, 87, 0.28);
  color: #f06a6a;
}

.state-area {
  min-height: 260px;
  display: grid;
  place-items: center;
  text-align: center;
}

.preview-overlay,
.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(10, 10, 9, 0.86);
}

.preview-modal {
  position: relative;
  max-width: min(980px, 94vw);
  max-height: 92vh;
  overflow: hidden;
}

.preview-modal img {
  max-width: 100%;
  max-height: 70vh;
  display: block;
  object-fit: contain;
  background: #000;
}

.preview-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid rgba(232, 230, 220, 0.22);
  background: rgba(20, 20, 19, 0.7);
  color: var(--color-light);
  cursor: pointer;
  font-size: 22px;
}

.preview-info,
.confirm-box {
  padding: 20px;
}

.confirm-box {
  width: min(380px, 100%);
}

.confirm-box h3 {
  color: var(--color-light);
  margin: 0 0 10px;
}

@media (max-width: 720px) {
  .history-grid {
    grid-template-columns: 1fr;
  }
}
</style>
