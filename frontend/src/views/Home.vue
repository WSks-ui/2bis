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

        <div class="workflow-row">
          <button
            v-for="item in workflowOptions"
            :key="item.workflow_type"
            :class="{ active: selectedWorkflowType === item.workflow_type }"
            @click="selectWorkflow(item)"
          >
            <strong>{{ item.name }}</strong>
            <span>{{ item.description }}</span>
          </button>
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
              <span>{{ qualityCost(item.value) }} 额度 · {{ qualitySource }}</span>
            </button>
          </div>

          <div class="ratio-row">
            <button
              v-for="group in sizeGroups"
              :key="group.ratio"
              :class="{ active: selectedRatio === group.ratio }"
              @click="selectRatio(group.ratio)"
            >
              <strong>{{ group.ratio }}</strong>
              <span>{{ group.name }}</span>
            </button>
          </div>

          <div class="resolution-row">
            <button
              v-for="item in availableSizes"
              :key="item.value"
              :class="{ active: size === item.value }"
              @click="size = item.value"
            >
              <strong>{{ item.label }}</strong>
              <span>{{ formatImageSize(item.value) }} · {{ imageMegapixels(item.value) }}</span>
            </button>
          </div>

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
import api from '../api'
import { IMAGE_SIZE_GROUPS, formatImageSize, imageMegapixels } from '../constants/imageSizes'
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
const selectedRatio = ref('1:1')
const selectedWorkflowType = ref('standard')
const selectedWorkflowPreset = ref('')
const workflowOptions = ref([
  {
    workflow_type: 'standard',
    workflow_preset: null,
    name: '标准生成',
    description: '低/中质量优先体验积分',
    costs: { low: 1, medium: 2, high: 3 },
    uses_experience_points: true
  },
  {
    workflow_type: 'professional',
    workflow_preset: 'pro-detail',
    name: '专业工作流',
    description: '按订阅额度扣费',
    costs: { low: 1, medium: 2, high: 3 },
    uses_experience_points: false
  }
])
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
  { label: '低质量', value: 'low' },
  { label: '中质量', value: 'medium' },
  { label: '高质量', value: 'high' }
]

const sizeGroups = IMAGE_SIZE_GROUPS

const needImage = computed(() => mode.value !== 'text2img')
const canSubmit = computed(() => {
  if (needImage.value) return Boolean(prompt.value.trim() && refImage.value)
  return Boolean(prompt.value.trim())
})
const sortedTasks = computed(() => [...tasksStore.tasks].reverse())
const selectedWorkflow = computed(() => {
  return workflowOptions.value.find((item) => item.workflow_type === selectedWorkflowType.value) || workflowOptions.value[0]
})
const selectedSizeGroup = computed(() => {
  return sizeGroups.find((group) => group.ratio === selectedRatio.value) || sizeGroups[0]
})
const availableSizes = computed(() => selectedSizeGroup.value?.sizes || [])
const qualitySource = computed(() => {
  if (selectedWorkflow.value?.uses_experience_points && quality.value !== 'high') {
    return '优先体验积分'
  }
  return '订阅额度'
})
const placeholder = computed(() => {
  if (mode.value === 'text2img') return '描述你想生成的画面'
  if (mode.value === 'ref2img') return '结合参考图描述新画面'
  return '描述要如何编辑原图'
})

onMounted(async () => {
  await userStore.fetchUserInfo()
  await pointsStore.fetchBalance()
  await fetchWorkflowOptions()
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

async function fetchWorkflowOptions() {
  try {
    const res = await api.get('/points/plans')
    const presets = res.data?.workflow_presets
    if (Array.isArray(presets) && presets.length) {
      workflowOptions.value = presets
      if (!presets.some((item) => item.workflow_type === selectedWorkflowType.value)) {
        selectWorkflow(presets[0])
      }
    }
  } catch (_) {}
}

function selectWorkflow(item) {
  selectedWorkflowType.value = item.workflow_type
  selectedWorkflowPreset.value = item.workflow_preset || ''
}

function qualityCost(value) {
  return selectedWorkflow.value?.costs?.[value] ?? 0
}

function selectRatio(ratio) {
  selectedRatio.value = ratio
  const group = sizeGroups.find((item) => item.ratio === ratio)
  if (group && !group.sizes.some((item) => item.value === size.value)) {
    size.value = group.sizes[0].value
  }
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
    refPreview: refPreview.value,
    workflowType: selectedWorkflowType.value,
    workflowPreset: selectedWorkflowPreset.value
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
.workflow-row,
.controls-row,
.quality-row,
.ratio-row,
.resolution-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.mode-row button,
.workflow-row button,
.quality-row button,
.ratio-row button,
.resolution-row button,
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
.workflow-row button.active,
.quality-row button.active,
.ratio-row button.active,
.resolution-row button.active {
  color: var(--color-orange);
  border-color: rgba(217, 119, 87, 0.34);
  background: rgba(217, 119, 87, 0.1);
}

.workflow-row button {
  flex: 1 1 220px;
  min-height: 66px;
  padding: 11px 14px;
  display: grid;
  gap: 4px;
  cursor: pointer;
  text-align: left;
}

.workflow-row span {
  color: var(--color-mid);
  font-size: 12px;
  line-height: 1.4;
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

.ratio-row {
  flex: 1 1 100%;
}

.resolution-row {
  flex: 1 1 560px;
}

.quality-row button {
  min-width: 130px;
  padding: 9px 12px;
  display: grid;
  gap: 3px;
  cursor: pointer;
  text-align: left;
}

.ratio-row button {
  min-width: 92px;
  min-height: 54px;
  padding: 8px 11px;
  display: grid;
  gap: 2px;
  cursor: pointer;
  text-align: left;
}

.resolution-row button {
  min-width: 142px;
  min-height: 54px;
  padding: 8px 11px;
  display: grid;
  gap: 2px;
  cursor: pointer;
  text-align: left;
}

.quality-row span {
  font-size: 11px;
  color: var(--color-mid);
}

.ratio-row span,
.resolution-row span {
  color: var(--color-mid);
  font-size: 11px;
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
  .ratio-row button,
  .resolution-row button,
  .size-select,
  .btn-generate {
    width: 100%;
  }
}
</style>
