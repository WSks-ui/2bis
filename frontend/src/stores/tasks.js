import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'
import { usePointsStore } from './points'

let nextId = 1

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref([])

  function addTask({ mode, prompt, quality, size, refImage, refPreview }) {
    const id = `task-${Date.now()}-${nextId++}`
    const task = {
      id,
      mode,
      prompt,
      quality,
      size,
      refImage: refImage || null,
      refPreview: refPreview || '',
      status: 'queued',
      imageUrl: '',
      error: '',
      createdAt: Date.now(),
    }
    tasks.value.push(task)
    executeTask(id)
  }

  function removeTask(id) {
    const idx = tasks.value.findIndex((t) => t.id === id)
    if (idx !== -1) tasks.value.splice(idx, 1)
  }

  function clearCompleted() {
    tasks.value = tasks.value.filter(
      (t) => t.status !== 'done' && t.status !== 'failed'
    )
  }

  async function executeTask(id) {
    const task = tasks.value.find((t) => t.id === id)
    if (!task) return
    task.status = 'generating'

    try {
      let res
      if (task.mode === 'text2img') {
        res = await api.post('/generate', {
          prompt: task.prompt,
          quality: task.quality,
          size: task.size,
        })
      } else {
        const formData = new FormData()
        formData.append('image', task.refImage)
        formData.append('prompt', task.prompt)
        formData.append('quality', task.quality)
        formData.append('size', task.size)
        res = await api.post('/edits', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }
      task.imageUrl = res.data.image_url
      task.status = 'done'
    } catch (e) {
      task.status = 'failed'
      task.error = e.response?.data?.detail || '生成失败，请重试'
    }

    const pointsStore = usePointsStore()
    try {
      await pointsStore.fetchBalance()
    } catch (_) {
      /* ignore balance fetch errors */
    }
  }

  return {
    tasks,
    addTask,
    removeTask,
    clearCompleted,
  }
})
