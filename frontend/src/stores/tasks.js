import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'
import { usePointsStore } from './points'

const POLL_INTERVAL = 5000
const ACTIVE_STATUSES = ['pending', 'processing']

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref([])
  const pollingTimers = new Map()

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
      error: data.error_message || '',
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
    stopPolling(id)
    try {
      await api.delete(`/generate/tasks/${id}`)
    } catch (_) {}
    const idx = tasks.value.findIndex((t) => t.id === id)
    if (idx !== -1) tasks.value.splice(idx, 1)
  }

  function clearCompleted() {
    tasks.value
      .filter((t) => t.status === 'done' || t.status === 'failed')
      .forEach((t) => stopPolling(t.id))
    tasks.value = tasks.value.filter(
      (t) => t.status !== 'done' && t.status !== 'failed'
    )
  }

  async function fetchTasks() {
    const res = await api.get('/generate/tasks')
    const remoteTasks = res.data.map((item) => normalizeTask(item))
    tasks.value = remoteTasks
    remoteTasks.forEach((task) => {
      if (isActive(task)) startPolling(task.id)
    })
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
    if (pollingTimers.has(id)) return
    const timer = window.setInterval(() => {
      fetchTask(id).catch(() => {})
    }, POLL_INTERVAL)
    pollingTimers.set(id, timer)
    fetchTask(id).catch(() => {})
  }

  function stopPolling(id) {
    const timer = pollingTimers.get(id)
    if (timer) {
      window.clearInterval(timer)
      pollingTimers.delete(id)
    }
  }

  function stopAllPolling() {
    pollingTimers.forEach((timer) => window.clearInterval(timer))
    pollingTimers.clear()
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
    stopAllPolling,
  }
})
