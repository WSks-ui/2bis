<template>
  <div class="history-page paper-page">
    <main class="history-shell">
      <aside class="filter-panel surface-card">
        <div class="filter-head">
          <h2>筛选</h2>
          <button type="button" @click="resetFilters">清空</button>
        </div>

        <label>
          时间范围
          <select v-model="filters.range" @change="applyFilters">
            <option value="all">全部时间</option>
            <option value="today">今天</option>
            <option value="week">最近 7 天</option>
            <option value="month">最近 30 天</option>
          </select>
        </label>

        <label>
          工作流
          <select v-model="filters.workflow" @change="applyFilters">
            <option value="all">全部</option>
            <option value="standard">标准生成</option>
            <option value="professional">专业工作流</option>
          </select>
        </label>

        <label>
          质量
          <select v-model="filters.quality" @change="applyFilters">
            <option value="all">全部</option>
            <option value="low">低质量</option>
            <option value="medium">中质量</option>
            <option value="high">高质量</option>
          </select>
        </label>

        <label>
          扣费来源
          <select v-model="filters.source" @change="applyFilters">
            <option value="all">全部</option>
            <option value="free_points">体验积分</option>
            <option value="quota">订阅额度</option>
            <option value="points">普通积分</option>
          </select>
        </label>

        <button class="export-button" type="button" @click="exportHistory">导出记录</button>
      </aside>

      <section class="history-main">
        <header class="history-hero">
          <div>
            <p class="eyebrow">Generation History</p>
            <h1>历史记录</h1>
            <p>查看生成结果、扣费来源与工作流信息。失败任务不进入历史，生成页任务日志会显示退款状态。</p>
          </div>
          <div class="history-stats surface-card">
            <div>
              <span>记录</span>
              <strong>{{ totalRecords }}</strong>
            </div>
            <div>
              <span>订阅额度</span>
              <strong>{{ quotaCostTotal }}</strong>
            </div>
            <div>
              <span>体验积分</span>
              <strong>{{ freePointCostTotal }}</strong>
            </div>
          </div>
        </header>

        <div v-if="loading" class="state-area surface-card">加载中...</div>

        <div v-else-if="!filteredRecords.length" class="state-area surface-card">
          <p>暂无匹配记录</p>
          <router-link to="/" class="btn-black start-link">开始创作</router-link>
        </div>

        <section v-else class="history-table surface-card" :class="{ 'is-page-loading': pageLoading }">
          <article v-for="record in pagedRecords" :key="record.id" class="history-row">
            <button class="thumb-button" @click="openPreview(record)">
              <img :src="record.thumbnail_url || record.image_url" :alt="record.prompt" loading="lazy" decoding="async" />
            </button>

            <div class="record-prompt">
              <p>{{ record.prompt }}</p>
              <div class="record-tags">
                <span>{{ qualityLabel(record.quality) }}</span>
                <span>{{ workflowLabel(record.workflow_type) }}</span>
                <span>{{ sourceLabel(record.balance_source) }}</span>
              </div>
            </div>

            <span class="cost-cell">{{ record.points_cost }} 额度</span>
            <span class="time-cell">{{ formatTime(record.created_at) }}</span>
            <div class="row-actions">
              <button @click="openPreview(record)">查看</button>
              <button @click="downloadImage(record)">下载</button>
              <button class="danger" @click="confirmDelete(record)">删除</button>
            </div>
          </article>
        </section>

        <nav v-if="totalPages > 1" class="pagination-bar" aria-label="历史分页">
          <button type="button" :disabled="currentPage <= 1 || pageLoading" @click="goToPage(currentPage - 1)">‹</button>
          <button
            v-for="item in paginationItems"
            :key="`${item.type}-${item.value}`"
            type="button"
            :class="{ active: item.value === currentPage, ellipsis: item.type === 'ellipsis' }"
            :disabled="item.type === 'ellipsis' || pageLoading"
            @click="item.type === 'page' && goToPage(item.value)"
          >
            {{ item.label }}
          </button>
          <button type="button" :disabled="currentPage >= totalPages || pageLoading" @click="goToPage(currentPage + 1)">›</button>
        </nav>
      </section>
    </main>

    <div v-if="previewRecord" class="preview-overlay" @click.self="closePreview">
      <div class="preview-modal">
        <button class="preview-close" @click="closePreview">×</button>
        <div class="preview-image-frame">
          <img
            :src="previewImageUrl || previewRecord.thumbnail_url || previewRecord.image_url"
            :alt="previewRecord.prompt"
            decoding="async"
          />
          <span v-if="previewLoading" class="preview-loading">正在载入原图...</span>
        </div>
        <div class="preview-info">
          <p>{{ previewRecord.prompt }}</p>
          <div class="record-tags">
            <span>{{ qualityLabel(previewRecord.quality) }}</span>
            <span>{{ previewRecord.points_cost }} 额度</span>
            <span>{{ sourceLabel(previewRecord.balance_source) }}</span>
            <span>{{ workflowLabel(previewRecord.workflow_type) }}</span>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from '../services/toast'
import api from '../api'
import { getCachedFullImageUrl, preloadThumbnails, removeCachedImage, warmFullImage } from '../services/imageCache'
import {
  fetchHistoryPage,
  readCachedHistoryPage,
  removeHistoryRecordFromCache
} from '../services/historyCache'

defineOptions({ name: 'History' })

const filters = reactive({
  range: 'all',
  workflow: 'all',
  quality: 'all',
  source: 'all'
})

const initialHistoryPage = readCachedHistoryPage({
  page: 1,
  page_size: 12,
  range: filters.range,
  workflow: filters.workflow,
  quality: filters.quality,
  source: filters.source
})

const records = ref(initialHistoryPage?.records || [])
const loading = ref(!initialHistoryPage)
const pageLoading = ref(false)
const previewRecord = ref(null)
const previewImageUrl = ref('')
const previewLoading = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)
const currentPage = ref(initialHistoryPage?.page || 1)
const pageSize = ref(initialHistoryPage?.page_size || 12)
const totalRecords = ref(initialHistoryPage?.total || 0)
const totalPages = ref(initialHistoryPage?.total_pages || 1)
let previewRequestId = 0
let historyRequestId = 0

const filteredRecords = computed(() => {
  return records.value.filter((record) => {
    if (filters.workflow !== 'all' && (record.workflow_type || 'standard') !== filters.workflow) return false
    if (filters.quality !== 'all' && record.quality !== filters.quality) return false
    if (filters.source !== 'all' && record.balance_source !== filters.source) return false
    return isInRange(record.created_at, filters.range)
  })
})

const pagedRecords = computed(() => filteredRecords.value)

const paginationItems = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const items = []
  const pushPage = (value) => {
    if (!items.some((item) => item.type === 'page' && item.value === value)) {
      items.push({ type: 'page', value, label: String(value) })
    }
  }
  const pushEllipsis = (key) => items.push({ type: 'ellipsis', value: key, label: '...' })

  if (total <= 7) {
    for (let page = 1; page <= total; page += 1) pushPage(page)
    return items
  }

  pushPage(1)
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  if (start > 2) pushEllipsis('left')
  for (let page = start; page <= end; page += 1) pushPage(page)
  if (end < total - 1) pushEllipsis('right')
  pushPage(total)
  return items
})

const quotaCostTotal = computed(() => {
  return filteredRecords.value
    .filter((record) => record.balance_source === 'quota')
    .reduce((total, record) => total + (record.points_cost || 0), 0)
})

const freePointCostTotal = computed(() => {
  return filteredRecords.value
    .filter((record) => record.balance_source === 'free_points')
    .reduce((total, record) => total + (record.points_cost || 0), 0)
})

onMounted(() => {
  loadHistoryPage()
})

async function loadHistoryPage(options = {}) {
  const requestId = ++historyRequestId
  const params = getHistoryParams()
  const cachedPage = readCachedHistoryPage(params)
  const hasVisibleRecords = records.value.length > 0

  if (cachedPage) {
    applyHistoryPage(cachedPage)
    loading.value = false
    pageLoading.value = true
  } else {
    loading.value = !hasVisibleRecords
    pageLoading.value = hasVisibleRecords
  }

  try {
    const page = await fetchHistoryPage(params, { force: options.force === true })
    if (requestId !== historyRequestId) return
    applyHistoryPage(page)
  } catch (e) {
    if (requestId !== historyRequestId) return
    if (!cachedPage) {
      records.value = []
      totalRecords.value = 0
      totalPages.value = 1
    }
    ElMessage.error(e.response?.data?.detail || '历史记录加载失败')
  } finally {
    if (requestId === historyRequestId) {
      loading.value = false
      pageLoading.value = false
    }
  }
}

function applyHistoryPage(page) {
  records.value = page.records || []
  totalRecords.value = page.total || 0
  currentPage.value = page.page || currentPage.value
  pageSize.value = page.page_size || pageSize.value
  totalPages.value = Math.max(1, page.total_pages || 1)
  preloadThumbnails(records.value)
}

function getHistoryParams() {
  return {
    page: currentPage.value,
    page_size: pageSize.value,
    range: filters.range,
    workflow: filters.workflow,
    quality: filters.quality,
    source: filters.source
  }
}

function resetFilters() {
  filters.range = 'all'
  filters.workflow = 'all'
  filters.quality = 'all'
  filters.source = 'all'
  applyFilters()
}

function applyFilters() {
  currentPage.value = 1
  loadHistoryPage()
}

function goToPage(page) {
  const nextPage = Math.min(Math.max(page, 1), totalPages.value)
  if (nextPage === currentPage.value) return
  currentPage.value = nextPage
  loadHistoryPage()
}

function isInRange(timeStr, range) {
  if (range === 'all') return true
  const timestamp = new Date(timeStr).getTime()
  if (Number.isNaN(timestamp)) return false
  const now = Date.now()
  const day = 24 * 60 * 60 * 1000
  if (range === 'today') return new Date(timeStr).toDateString() === new Date().toDateString()
  if (range === 'week') return now - timestamp <= 7 * day
  if (range === 'month') return now - timestamp <= 30 * day
  return true
}

async function openPreview(record) {
  const requestId = ++previewRequestId
  previewRecord.value = record
  previewImageUrl.value = getCachedFullImageUrl(record) || ''
  previewLoading.value = !previewImageUrl.value
  try {
    const loadedUrl = await warmFullImage(record)
    if (requestId === previewRequestId) {
      previewImageUrl.value = loadedUrl
    }
  } catch (_) {
    if (requestId === previewRequestId) {
      previewImageUrl.value = record.image_url || record.thumbnail_url || ''
    }
  } finally {
    if (requestId === previewRequestId) {
      previewLoading.value = false
    }
  }
}

function closePreview() {
  previewRequestId += 1
  previewRecord.value = null
  previewImageUrl.value = ''
  previewLoading.value = false
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
    totalRecords.value = Math.max(0, totalRecords.value - 1)
    removeHistoryRecordFromCache(deleteTarget.value.id)
    removeCachedImage(deleteTarget.value)
    if (previewRecord.value?.id === deleteTarget.value.id) closePreview()
    deleteTarget.value = null
    if (!records.value.length && currentPage.value > 1) {
      currentPage.value -= 1
      await loadHistoryPage({ force: true })
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败，请稍后重试')
  } finally {
    deleting.value = false
  }
}

function downloadImage(record) {
  if (!record.image_url) return
  warmFullImage(record).catch(() => {})
  const a = document.createElement('a')
  a.href = record.image_url
  a.download = `2bis-${record.id}.png`
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function exportHistory() {
  if (!filteredRecords.value.length) {
    ElMessage.info('当前没有可导出的记录')
    return
  }
  const content = filteredRecords.value.map((record) => ({
    id: record.id,
    prompt: record.prompt,
    quality: qualityLabel(record.quality),
    workflow: workflowLabel(record.workflow_type),
    source: sourceLabel(record.balance_source),
    cost: record.points_cost,
    created_at: record.created_at
  }))
  const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '2bis-history.json'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('已导出当前筛选记录')
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
  const map = { standard: '标准生成', professional: '专业工作流' }
  return map[type || 'standard'] || type
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
.history-shell {
  max-width: 1360px;
  margin: 0 auto;
  padding: 34px 28px 100px;
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 28px;
}

.filter-panel {
  position: sticky;
  top: 92px;
  align-self: start;
  padding: 22px;
  display: grid;
  gap: 18px;
}

.filter-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.filter-head h2 {
  margin: 0;
  font-size: 18px;
}

.filter-head button,
.export-button,
.row-actions button,
.btn-ghost,
.btn-danger {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-muted);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
}

.filter-head button {
  min-height: 30px;
  padding: 0 10px;
}

.filter-panel label {
  display: grid;
  gap: 8px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
}

.filter-panel select {
  width: 100%;
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.8);
  color: var(--color-ink);
  outline: none;
}

.export-button {
  min-height: 38px;
}

.history-main {
  min-width: 0;
}

.history-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: end;
  margin-bottom: 22px;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.history-hero h1 {
  margin: 0;
  font-size: clamp(34px, 5vw, 54px);
  letter-spacing: -0.06em;
}

.history-hero p {
  max-width: 620px;
  margin: 10px 0 0;
  color: var(--color-muted);
}

.history-stats {
  min-width: 330px;
  padding: 17px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.history-stats div {
  display: grid;
  gap: 5px;
}

.history-stats span {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.history-stats strong {
  color: var(--color-ink);
  font-family: var(--font-heading);
  font-size: 24px;
}

.state-area {
  min-height: 300px;
  display: grid;
  place-items: center;
  gap: 14px;
  color: var(--color-muted);
  text-align: center;
}

.start-link {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  padding: 0 20px;
  font-family: var(--font-ui);
  font-weight: 850;
}

.history-table {
  overflow: hidden;
  transition: opacity var(--transition-base);
}

.history-table.is-page-loading {
  opacity: 0.58;
}

.history-row {
  min-height: 88px;
  padding: 13px 16px;
  display: grid;
  grid-template-columns: 74px minmax(220px, 1fr) 86px 142px 160px;
  gap: 16px;
  align-items: center;
  border-bottom: 1px solid rgba(226, 229, 223, 0.76);
}

.history-row:last-child {
  border-bottom: 0;
}

.thumb-button {
  width: 68px;
  height: 68px;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: var(--color-paper-soft);
  cursor: pointer;
}

.thumb-button img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.record-prompt {
  min-width: 0;
}

.record-prompt p {
  margin: 0 0 9px;
  overflow: hidden;
  color: var(--color-ink);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.record-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.record-tags span {
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--color-paper-soft);
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 850;
}

.cost-cell,
.time-cell {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 760;
}

.row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 7px;
}

.row-actions button {
  min-height: 32px;
  padding: 0 9px;
}

.row-actions .danger,
.btn-danger {
  color: var(--color-red);
  border-color: rgba(200, 77, 60, 0.2);
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
  background: rgba(23, 23, 23, 0.46);
  backdrop-filter: blur(10px);
}

.preview-modal,
.confirm-box {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: var(--shadow-lg);
}

.preview-modal {
  position: relative;
  max-width: min(1040px, 94vw);
  max-height: 92vh;
  overflow: hidden;
}

.preview-image-frame {
  position: relative;
  display: grid;
  place-items: center;
  background: #111;
}

.preview-image-frame img {
  max-width: 100%;
  max-height: 70vh;
  display: block;
  object-fit: contain;
}

.preview-loading {
  position: absolute;
  left: 50%;
  bottom: 18px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
  transform: translateX(-50%);
}

.pagination-bar {
  width: max-content;
  max-width: 100%;
  margin: 22px auto 0;
  display: flex;
  overflow: hidden;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-sm);
}

.pagination-bar button {
  min-width: 54px;
  height: 44px;
  border: 0;
  border-right: 1px solid var(--color-line);
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 850;
}

.pagination-bar button:last-child {
  border-right: 0;
}

.pagination-bar button.active {
  background: rgba(28, 180, 151, 0.1);
  color: #087e70;
  box-shadow: inset 0 0 0 1px #14b8a6;
}

.pagination-bar button.ellipsis {
  cursor: default;
}

.pagination-bar button:disabled {
  cursor: not-allowed;
  opacity: 0.46;
}

.preview-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(255, 255, 255, 0.58);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.78);
  color: var(--color-ink);
  cursor: pointer;
  font-size: 22px;
  backdrop-filter: blur(10px);
}

.preview-info,
.confirm-box {
  padding: 20px;
}

.preview-info p,
.confirm-box p {
  margin: 0 0 12px;
  color: var(--color-muted);
}

.confirm-box {
  width: min(390px, 100%);
}

.confirm-box h3 {
  margin: 0 0 10px;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.btn-ghost,
.btn-danger {
  min-height: 38px;
  padding: 0 14px;
}

@media (max-width: 1080px) {
  .history-shell {
    grid-template-columns: 1fr;
  }

  .filter-panel {
    position: static;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    align-items: end;
  }

  .filter-head {
    grid-column: span 5;
  }

  .history-hero {
    align-items: stretch;
    flex-direction: column;
  }

  .history-stats {
    min-width: 0;
  }
}

@media (max-width: 780px) {
  .history-shell {
    padding: 24px 14px 96px;
  }

  .filter-panel {
    grid-template-columns: 1fr 1fr;
  }

  .filter-head {
    grid-column: span 2;
  }

  .history-row {
    grid-template-columns: 64px minmax(0, 1fr);
    gap: 12px;
  }

  .cost-cell,
  .time-cell {
    display: none;
  }

  .row-actions {
    grid-column: 2;
    justify-content: flex-start;
  }

  .pagination-bar {
    width: 100%;
    justify-content: center;
  }

  .pagination-bar button {
    min-width: 42px;
  }
}

@media (max-width: 520px) {
  .filter-panel,
  .history-stats {
    grid-template-columns: 1fr;
  }

  .filter-head {
    grid-column: auto;
  }

  .history-row {
    grid-template-columns: 1fr;
  }

  .thumb-button {
    width: 100%;
    height: auto;
    aspect-ratio: 16 / 9;
  }

  .row-actions {
    grid-column: auto;
  }
}
</style>
