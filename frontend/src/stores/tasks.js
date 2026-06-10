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
      createdAt: data.created_at || local.createdAt || new Date().toISOString(),
      startedAt: data.started_at || null,
      finishedAt: data.finished_at || null,
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

  async function addTask({ mode, prompt, quality, size, refImage, refPreview }) {
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
      workflowType: 'standard',
      workflowCost: 0,
      workflowPreset: '',
      createdAt: new Date().toISOString(),
    }
    tasks.value.push(local)

    try {
      let res
      if (mode === 'text2img') {
        res = await api.post('/generate', { prompt, quality, size })
      } else {
        const formData = new FormData()
        formData.append('image', refImage)
        formData.append('prompt', prompt)
        formData.append('quality', quality)
        formData.append('size', size)
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
    const res = await api.get(`/generate/tasks/${id}`)
    const current = tasks.value.find((t) => t.id === id)
    const task = normalizeTask(res.data, current || {})
    upsertTask(task)
    if (!isActive(task)) {
      stopPolling(id)
      await refreshBalance()
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
