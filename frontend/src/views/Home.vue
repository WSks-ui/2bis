<template>
  <div class="home-page">
    <NavBar />

    <main class="studio-container">
      <section class="command-panel">
        <div class="mode-row">
          <button v-for="item in modes" :key="item.value" :class="{ active: mode === item.value }" @click="switchMode(item.value)">
            {{ item.label }}
          </button>
        </div>

        <div v-if="needImage" class="upload-row" @click="triggerUpload">
          <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="handleFileSelect" />
          <img v-if="refPreview" :src="refPreview" alt="参考图" />
          <span>{{ refPreview ? '更换图片' : '上传图片' }}</span>
        </div>

        <textarea
          ref="promptInput"
          v-model="prompt"
          class="prompt-input"
          :placeholder="placeholder"
          rows="3"
          @keydown.enter.exact.prevent="handleSubmit"
        ></textarea>

        <div class="controls-row">
          <div class="quality-row">
            <button v-for="item in qualities" :key="item.value" :class="{ active: quality === item.value }" @click="quality = item.value">
              <strong>{{ item.label }}</strong>
              <span>{{ item.source }}</span>
            </button>
          </div>

          <select v-model="size" class="size-select">
            <option v-for="item in sizes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>

          <button class="btn-generate" :disabled="!canSubmit" @click="handleSubmit">生成</button>
        </div>
      </section>

      <section v-if="tasksStore.tasks.length === 0" class="empty-state">
        <h1>创作画布</h1>
        <p>输入提示词，选择质量和尺寸后开始生成。</p>
      </section>

      <section v-else class="gallery-grid">
        <TaskCard
          v-for="task in sortedTasks"
          :key="task.id"
          :task="task"
          @remove="tasksStore.removeTask(task.id)"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../components/NavBar.vue'
import TaskCard from '../components/TaskCard.vue'
import { useTasksStore } from '../stores/tasks'
import { useUserStore } from '../stores/user'
import { usePointsStore } from '../stores/points'

const tasksStore = useTasksStore()
const userStore = useUserStore()
const pointsStore = usePointsStore()

const mode = ref('text2img')
const prompt = ref('')
const quality = ref('low')
const size = ref('1024x1024')
const refImage = ref(null)
const refPreview = ref('')
const fileInput = ref(null)
const promptInput = ref(null)

const modes = [
  { label: '文生图', value: 'text2img' },
  { label: '参考图', value: 'ref2img' },
  { label: '编辑', value: 'edit' }
]

const qualities = [
  { label: '低质量', value: 'low', source: '优先体验积分' },
  { label: '中质量', value: 'medium', source: '优先体验积分' },
  { label: '高质量', value: 'high', source: '订阅额度' }
]

const sizes = [
  { label: '1024×1024', value: '1024x1024' },
  { label: '1344×768', value: '1344x768' },
  { label: '768×1344', value: '768x1344' },
  { label: '2048×2048', value: '2048x2048' }
]

const needImage = computed(() => mode.value !== 'text2img')
const canSubmit = computed(() => {
  if (needImage.value) return Boolean(prompt.value.trim() && refImage.value)
  return Boolean(prompt.value.trim())
})
const sortedTasks = computed(() => [...tasksStore.tasks].reverse())
const placeholder = computed(() => {
  if (mode.value === 'text2img') return '描述你想生成的画面'
  if (mode.value === 'ref2img') return '结合参考图描述新画面'
  return '描述要如何编辑原图'
})

onMounted(async () => {
  await userStore.fetchUserInfo()
  await pointsStore.fetchBalance()
  tasksStore.fetchTasks().catch(() => {})
})

onBeforeUnmount(() => {
  tasksStore.stopAllPolling()
})

function switchMode(nextMode) {
  mode.value = nextMode
  if (nextMode === 'text2img') {
    refImage.value = null
    refPreview.value = ''
  }
  nextTick(() => promptInput.value?.focus())
}

function triggerUpload() {
  fileInput.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!file.type.match(/image\/(png|jpeg|webp)/)) {
    ElMessage.warning('仅支持 PNG / JPG / WebP')
    return
  }
  refImage.value = file
  const reader = new FileReader()
  reader.onload = (readerEvent) => {
    refPreview.value = readerEvent.target.result
  }
  reader.readAsDataURL(file)
}

function handleSubmit() {
  if (!prompt.value.trim()) return
  if (needImage.value && !refImage.value) {
    ElMessage.warning('请先上传图片')
    return
  }

  tasksStore.addTask({
    mode: mode.value,
    prompt: prompt.value.trim(),
    quality: quality.value,
    size: size.value,
    refImage: refImage.value,
    refPreview: refPreview.value
  })

  prompt.value = ''
  if (mode.value === 'text2img') {
    refImage.value = null
    refPreview.value = ''
  }
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: var(--color-dark);
}

.studio-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 28px 24px 80px;
}

.command-panel {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-lg);
  background: rgba(232, 230, 220, 0.04);
}

.mode-row,
.controls-row,
.quality-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.mode-row button,
.quality-row button,
.btn-generate,
.size-select {
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-md);
  background: rgba(250, 249, 245, 0.04);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-weight: 700;
}

.mode-row button {
  padding: 9px 16px;
  cursor: pointer;
}

.mode-row button.active,
.quality-row button.active {
  color: var(--color-orange);
  border-color: rgba(217, 119, 87, 0.34);
  background: rgba(217, 119, 87, 0.1);
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 76px;
  padding: 12px;
  border: 1px dashed rgba(106, 155, 204, 0.34);
  border-radius: var(--radius-md);
  color: var(--color-blue);
  cursor: pointer;
  font-family: var(--font-heading);
  font-weight: 700;
}

.upload-row img {
  width: 64px;
  height: 52px;
  object-fit: cover;
  border-radius: var(--radius-sm);
}

.prompt-input {
  width: 100%;
  min-height: 112px;
  padding: 16px;
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-md);
  resize: vertical;
  background: rgba(250, 249, 245, 0.04);
  color: var(--color-light);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.7;
  outline: none;
}

.prompt-input:focus {
  border-color: rgba(217, 119, 87, 0.45);
}

.quality-row {
  flex: 1;
}

.quality-row button {
  min-width: 130px;
  padding: 9px 12px;
  display: grid;
  gap: 3px;
  cursor: pointer;
  text-align: left;
}

.quality-row span {
  font-size: 11px;
  color: var(--color-mid);
}

.size-select {
  min-height: 44px;
  padding: 0 12px;
}

.btn-generate {
  min-height: 44px;
  padding: 0 24px;
  border-color: transparent;
  background: var(--color-orange);
  color: var(--color-dark);
  cursor: pointer;
}

.btn-generate:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.empty-state {
  min-height: 360px;
  display: grid;
  place-items: center;
  text-align: center;
  color: var(--color-mid);
}

.empty-state h1 {
  margin: 0 0 10px;
  color: var(--color-light);
  font-family: var(--font-heading);
  font-size: 34px;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px;
  margin-top: 24px;
}

@media (max-width: 720px) {
  .controls-row {
    align-items: stretch;
    flex-direction: column;
  }

  .quality-row button,
  .size-select,
  .btn-generate {
    width: 100%;
  }
}
</style>
