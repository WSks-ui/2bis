import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'
import { usePointsStore } from './points'

const POLL_INTERVAL = 5000
const HIDDEN_POLL_INTERVAL = 15000
const ACTIVE_STATUSES = ['pending', 'processing']
const TASKS_CACHE_MAX_AGE = 30 * 1000

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref([])
  let pollingTimer = null
  let pollingInFlight = false
  let visibilityListening = false
  let tasksRequest = null
  let lastFetchedAt = 0

  function normalizeTask(data, local = {}) {
    return {
      id: data.id,
      mode: data.mode || local.mode || 'text2img',
      prompt: data.prompt || local.prompt || '',
      quality: data.quality || local.quality || 'low',
      size: data.size || local.size || '1024x1024',
      refPreview: local.refPreview || '',
      status: mapStatus(data.status),
      rawStatus: data.status,
      imageUrl: data.image_url || '',
      error: ['failed', 'refunded'].includes(data.status) ? data.error_message || '' : '',
      pointsCost: data.points_cost || 0,
      balanceSource: data.balance_source || '',
      workflowType: data.workflow_type || 'standard',
      workflowCost: data.workflow_cost || data.points_cost || 0,
      workflowPreset: data.workflow_preset || '',
      upstreamModel: data.upstream_model || '',
      upstreamEndpoint: data.upstream_endpoint || '',
      upstreamRequestQuality: data.upstream_request_quality || '',
      upstreamRequestSize: data.upstream_request_size || '',
      upstreamResponseFormat: data.upstream_response_format || '',
      upstreamRequestId: data.upstream_request_id || '',
      upstreamElapsedSeconds: data.upstream_elapsed_seconds ?? null,
      progressStage: data.progress_stage || '',
      progressMessage: data.progress_message || '',
      createdAt: data.created_at || local.createdAt || new Date().toISOString(),
      startedAt: data.started_at || null,
      finishedAt: data.finished_at || null,
      lastPolledAt: new Date().toISOString(),
      pollError: '',
    }
  }

  function mapStatus(status) {
    if (status === 'success') return 'done'
    if (status === 'failed' || status === 'refunded') return 'failed'
    if (status === 'processing') return 'generating'
    return 'queued'
  }

  function isActive(task) {
    return ACTIVE_STATUSES.includes(task.rawStatus)
  }

  function activeTaskIds() {
    return tasks.value.filter(isActive).map((task) => task.id)
  }

  function upsertTask(task) {
    const idx = tasks.value.findIndex((t) => t.id === task.id)
    if (idx === -1) {
      tasks.value.push(task)
    } else {
      tasks.value[idx] = { ...tasks.value[idx], ...task }
    }
  }

  async function addTask({
    mode,
    prompt,
    quality,
    size,
    refImage,
    refPreview,
    workflowType = 'standard',
    workflowPreset = '',
  }) {
    const local = {
      id: `local-${Date.now()}`,
      mode,
      prompt,
      quality,
      size,
      refPreview: refPreview || '',
      status: 'queued',
      rawStatus: 'pending',
      imageUrl: '',
      error: '',
      workflowType,
      workflowCost: 0,
      workflowPreset,
      upstreamModel: '',
      upstreamEndpoint: '',
      upstreamRequestQuality: '',
      upstreamRequestSize: '',
      upstreamResponseFormat: '',
      upstreamRequestId: '',
      upstreamElapsedSeconds: null,
      progressStage: '',
      progressMessage: '',
      createdAt: new Date().toISOString(),
      lastPolledAt: null,
      pollError: '',
    }
    tasks.value.push(local)

    try {
      let res
      if (mode === 'text2img') {
        res = await api.post('/generate', {
          prompt,
          quality,
          size,
          workflow_type: workflowType,
          workflow_preset: workflowPreset || null,
        })
      } else {
        const formData = new FormData()
        formData.append('image', refImage)
        formData.append('prompt', prompt)
        formData.append('quality', quality)
        formData.append('size', size)
        formData.append('workflow_type', workflowType)
        if (workflowPreset) formData.append('workflow_preset', workflowPreset)
        res = await api.post('/edits', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }

      const task = normalizeTask(res.data, local)
      const localIdx = tasks.value.findIndex((t) => t.id === local.id)
      if (localIdx !== -1) tasks.value.splice(localIdx, 1, task)
      else upsertTask(task)
      startPolling(task.id)
      await refreshBalance()
    } catch (e) {
      const localTask = tasks.value.find((t) => t.id === local.id)
      if (localTask) {
        localTask.status = 'failed'
        localTask.rawStatus = 'failed'
        localTask.error = e.response?.data?.detail || '任务提交失败，请重试'
      }
      await refreshBalance()
    }
  }

  async function removeTask(id) {
    try {
      await api.delete(`/generate/tasks/${id}`)
    } catch (_) {}
    const idx = tasks.value.findIndex((t) => t.id === id)
    if (idx !== -1) tasks.value.splice(idx, 1)
    stopPolling()
  }

  function clearCompleted() {
    tasks.value = tasks.value.filter(
      (t) => t.status !== 'done' && t.status !== 'failed'
    )
    stopPolling()
  }

  async function fetchTasks() {
    if (tasksRequest) return tasksRequest
    if (lastFetchedAt && Date.now() - lastFetchedAt <= TASKS_CACHE_MAX_AGE) {
      resumePolling()
      return tasks.value
    }

    tasksRequest = api.get('/generate/tasks')
      .then((res) => {
        const remoteTasks = res.data.map((item) => normalizeTask(item))
        tasks.value = remoteTasks
        lastFetchedAt = Date.now()
        resumePolling()
        return remoteTasks
      })
      .finally(() => {
        tasksRequest = null
      })
    return tasksRequest
  }

  async function fetchTask(id) {
    try {
      const res = await api.get(`/generate/tasks/${id}`)
      const current = tasks.value.find((t) => t.id === id)
      const task = normalizeTask(res.data, current || {})
      upsertTask(task)
      if (!isActive(task)) {
        stopPolling(id)
        await refreshBalance()
      }
    } catch (e) {
      const task = tasks.value.find((t) => t.id === id)
      if (task) {
        task.pollError = e.response?.data?.detail || e.message || '状态刷新失败'
      }
      throw e
    }
  }

  function startPolling(id) {
    ensureVisibilityListener()
    schedulePolling()
    fetchTask(id).catch(() => {})
  }

  function resumePolling() {
    if (!activeTaskIds().length) return
    ensureVisibilityListener()
    schedulePolling(0)
  }

  function stopPolling() {
    if (activeTaskIds().length) return
    clearPollingTimer()
  }

  function stopAllPolling() {
    clearPollingTimer()
    if (visibilityListening && typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      visibilityListening = false
    }
  }

  function clearPollingTimer() {
    if (!pollingTimer) return
    window.clearTimeout(pollingTimer)
    pollingTimer = null
  }

  function schedulePolling(delay = pollDelay()) {
    if (pollingTimer || !activeTaskIds().length) return
    pollingTimer = window.setTimeout(runPollingLoop, delay)
  }

  async function runPollingLoop() {
    pollingTimer = null
    const ids = activeTaskIds()
    if (!ids.length) return
    if (pollingInFlight) {
      schedulePolling()
      return
    }

    pollingInFlight = true
    try {
      await Promise.allSettled(ids.map((id) => fetchTask(id)))
    } finally {
      pollingInFlight = false
      if (activeTaskIds().length) schedulePolling()
    }
  }

  function pollDelay() {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      return HIDDEN_POLL_INTERVAL
    }
    return POLL_INTERVAL
  }

  function ensureVisibilityListener() {
    if (visibilityListening || typeof document === 'undefined') return
    document.addEventListener('visibilitychange', handleVisibilityChange)
    visibilityListening = true
  }

  function handleVisibilityChange() {
    if (document.visibilityState !== 'visible' || !activeTaskIds().length) return
    clearPollingTimer()
    runPollingLoop()
  }

  async function refreshBalance() {
    const pointsStore = usePointsStore()
    try {
      await pointsStore.fetchBalance()
    } catch (_) {}
  }

  return {
    tasks,
    addTask,
    removeTask,
    clearCompleted,
    fetchTasks,
    resumePolling,
    stopAllPolling,
  }
})
