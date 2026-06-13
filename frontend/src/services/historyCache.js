import api from '../api'
import { preloadThumbnails } from './imageCache'

const HISTORY_PAGE_CACHE_LIMIT = 16
const DEFAULT_PAGE_SIZE = 12
const DEFAULT_FILTER = 'all'
const DEFAULT_MAX_AGE = 30 * 1000

const pageCache = new Map()
const pendingRequests = new Map()
let cacheEpoch = 0

export function getDefaultHistoryParams() {
  return normalizeHistoryParams()
}

export function readCachedHistoryPage(params = {}) {
  const entry = pageCache.get(getHistoryCacheKey(params))
  return entry ? clonePage(entry.data) : null
}

export function isHistoryPageFresh(params = {}, maxAge = DEFAULT_MAX_AGE) {
  const entry = pageCache.get(getHistoryCacheKey(params))
  return Boolean(entry && Date.now() - entry.updatedAt <= maxAge)
}

export async function fetchHistoryPage(params = {}, options = {}) {
  const normalizedParams = normalizeHistoryParams(params)
  const cacheKey = getHistoryCacheKey(normalizedParams)
  const maxAge = options.maxAge ?? DEFAULT_MAX_AGE
  const cached = pageCache.get(cacheKey)

  if (!options.force && cached && Date.now() - cached.updatedAt <= maxAge) {
    return clonePage(cached.data)
  }

  if (!options.force && pendingRequests.has(cacheKey)) {
    return pendingRequests.get(cacheKey)
  }

  const requestEpoch = cacheEpoch
  const request = api
    .get('/history', { params: normalizedParams })
    .then((res) => {
      const page = normalizeHistoryPayload(res.data, normalizedParams)
      if (requestEpoch === cacheEpoch) {
        writeHistoryPage(cacheKey, page)
        preloadThumbnails(page.records)
      }
      return clonePage(page)
    })
    .finally(() => {
      if (pendingRequests.get(cacheKey) === request) {
        pendingRequests.delete(cacheKey)
      }
    })

  pendingRequests.set(cacheKey, request)
  return request
}

export async function warmHistoryPage(params = {}) {
  try {
    return await fetchHistoryPage(params)
  } catch (_) {
    return null
  }
}

export function removeHistoryRecordFromCache(recordId) {
  const updates = []
  pageCache.forEach((entry, cacheKey) => {
    const nextRecords = entry.data.records.filter((record) => record.id !== recordId)
    if (nextRecords.length === entry.data.records.length) return
    updates.push([cacheKey, {
      ...entry.data,
      records: nextRecords,
      total: Math.max(0, entry.data.total - 1),
      total_pages: Math.max(1, Math.ceil(Math.max(0, entry.data.total - 1) / entry.data.page_size))
    }])
  })

  updates.forEach(([cacheKey, nextPage]) => {
    writeHistoryPage(cacheKey, nextPage)
  })
}

export function clearHistoryCache() {
  cacheEpoch += 1
  pageCache.clear()
  pendingRequests.clear()
}

function normalizeHistoryParams(params = {}) {
  return {
    page: toPositiveInteger(params.page, 1),
    page_size: toPositiveInteger(params.page_size, DEFAULT_PAGE_SIZE),
    range: params.range || DEFAULT_FILTER,
    workflow: params.workflow || DEFAULT_FILTER,
    quality: params.quality || DEFAULT_FILTER,
    source: params.source || DEFAULT_FILTER
  }
}

function normalizeHistoryPayload(data, params) {
  const records = Array.isArray(data) ? data : (data.records || [])
  const pageSize = Array.isArray(data) ? params.page_size : toPositiveInteger(data.page_size, params.page_size)
  const total = Array.isArray(data) ? records.length : Math.max(0, Number(data.total || 0))

  return {
    records,
    total,
    page: Array.isArray(data) ? params.page : toPositiveInteger(data.page, params.page),
    page_size: pageSize,
    total_pages: Math.max(1, Array.isArray(data) ? 1 : toPositiveInteger(data.total_pages, Math.ceil(total / pageSize) || 1))
  }
}

function writeHistoryPage(cacheKey, page) {
  if (pageCache.has(cacheKey)) pageCache.delete(cacheKey)
  pageCache.set(cacheKey, {
    data: clonePage(page),
    updatedAt: Date.now()
  })
  trimPageCache()
}

function getHistoryCacheKey(params = {}) {
  const normalized = normalizeHistoryParams(params)
  return [
    normalized.page,
    normalized.page_size,
    normalized.range,
    normalized.workflow,
    normalized.quality,
    normalized.source
  ].join('|')
}

function clonePage(page) {
  return {
    ...page,
    records: [...(page.records || [])]
  }
}

function trimPageCache() {
  while (pageCache.size > HISTORY_PAGE_CACHE_LIMIT) {
    const oldestKey = pageCache.keys().next().value
    pageCache.delete(oldestKey)
  }
}

function toPositiveInteger(value, fallback) {
  const numberValue = Number(value)
  return Number.isInteger(numberValue) && numberValue > 0 ? numberValue : fallback
}
