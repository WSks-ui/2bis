<template>
  <div class="home-page paper-page">
    <main class="studio-shell">
      <aside v-reveal class="tool-panel surface-card">
        <section v-reveal="40" class="panel-section">
          <div class="section-title">生成模式</div>
          <div class="mode-grid">
            <button
              v-for="item in modes"
              :key="item.value"
              class="mode-button"
              :class="{ active: mode === item.value }"
              @click="switchMode(item.value)"
            >
              <span>{{ item.icon }}</span>
              {{ item.label }}
            </button>
          </div>
        </section>

        <section v-reveal="80" class="panel-section">
          <div class="section-title">工作流</div>
          <div class="workflow-list">
            <button
              v-for="item in workflowOptions"
              :key="`${item.workflow_type}-${item.workflow_preset || 'default'}`"
              class="workflow-card"
              :class="{ active: isWorkflowActive(item) }"
              @click="selectWorkflow(item)"
            >
              <span class="workflow-mark">{{ workflowMark(item.workflow_type) }}</span>
              <span class="workflow-copy">
                <strong>{{ item.name }}</strong>
                <small>{{ workflowBillingText(item) }}</small>
              </span>
              <span class="workflow-arrow">›</span>
            </button>
          </div>

          <div v-if="selectedWorkflow" class="workflow-detail">
            <div>
              <span>当前扣费</span>
              <strong>{{ currentCost }} 额度</strong>
            </div>
            <div>
              <span>扣费来源</span>
              <strong>{{ qualitySource }}</strong>
            </div>
            <div v-if="selectedWorkflow.workflow_type !== 'standard'">
              <span>策略</span>
              <strong>订阅额度</strong>
            </div>
          </div>
        </section>

        <section v-reveal="120" class="panel-section">
          <div class="section-title">质量</div>
          <div class="choice-grid three">
            <button
              v-for="item in qualities"
              :key="item.value"
              class="choice-card"
              :class="{ active: quality === item.value }"
              @click="quality = item.value"
            >
              <strong>{{ item.label }}</strong>
              <span>{{ qualityCost(item.value) }} 额度</span>
            </button>
          </div>
        </section>

        <section v-reveal="160" class="panel-section">
          <div class="section-title">尺寸比例</div>
          <div class="ratio-scroll">
            <button
              v-for="group in sizeGroups"
              :key="group.ratio"
              class="ratio-pill"
              :class="{ active: selectedRatio === group.ratio }"
              @click="selectRatio(group.ratio)"
            >
              {{ group.ratio }}
            </button>
          </div>
          <div class="resolution-list">
            <button
              v-for="item in availableSizes"
              :key="item.value"
              class="resolution-button"
              :class="{ active: size === item.value }"
              @click="size = item.value"
            >
              <span>{{ item.label }}</span>
              <strong>{{ formatImageSize(item.value) }}</strong>
            </button>
          </div>
        </section>

        <Transition name="modal-pop">
        <section v-if="needImage" class="panel-section">
          <div class="section-title">{{ imageInputTitle }}</div>
          <button class="upload-card" type="button" @click="triggerUpload">
            <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="handleFileSelect" />
            <img v-if="refPreview" :src="refPreview" alt="参考图" decoding="async" />
            <span v-else class="upload-placeholder">{{ imageInputHint }}<br />支持 JPG / PNG / WebP</span>
            <strong>{{ imageInputAction }}</strong>
          </button>
        </section>
        </Transition>
      </aside>

      <section class="studio-main">
        <section v-reveal="80" class="prompt-card surface-card">
          <div class="prompt-head">
            <label for="prompt-input">提示词</label>
            <span>{{ prompt.length }}/1000</span>
          </div>
          <textarea
            id="prompt-input"
            ref="promptInput"
            v-model="prompt"
            class="prompt-input"
            :placeholder="placeholder"
            maxlength="1000"
            rows="5"
            @keydown.enter.exact.prevent="handleSubmit"
          ></textarea>
          <div class="prompt-actions">
            <div class="quick-actions">
              <button type="button" @click="clearPrompt">清空</button>
              <button type="button" @click="fillPromptExample">随机提示</button>
              <button type="button" @click="polishPrompt">优化提示</button>
            </div>
            <span class="cost-note">{{ workflowSummary }}</span>
          </div>
        </section>

        <section v-reveal="130" class="generate-bar surface-card">
          <button class="btn-black generate-button" :disabled="!canSubmit" @click="handleSubmit">
            <span>{{ canSubmit ? `生成（消耗 ${currentCost} 额度）` : '填写提示词后生成' }}</span>
          </button>
          <button class="tune-button" type="button" @click="focusPanel">参数</button>
        </section>

        <section v-reveal="180" class="task-log surface-card">
          <div class="block-head">
            <div>
              <h2>任务日志</h2>
              <p>{{ activeTaskCount ? `${activeTaskCount} 个任务进行中` : '最近生成任务会显示在这里' }}</p>
            </div>
            <button v-if="tasksStore.tasks.length" type="button" @click="tasksStore.clearCompleted">清除已完成</button>
          </div>

          <div v-if="!recentTasks.length" class="empty-log">
            暂无任务。输入提示词后会先进入队列，失败任务会自动退款。
          </div>

          <TransitionGroup v-else name="list" tag="div" class="log-list">
            <article v-for="task in recentTasks" :key="task.id" class="log-row">
              <span class="status-dot" :class="`status-${task.status}`"></span>
              <div class="log-prompt">
                <strong>{{ statusLabel(task.status) }}</strong>
                <span>{{ task.prompt }}</span>
              </div>
              <span>{{ qualityLabel(task.quality) }}</span>
              <span>{{ task.workflowType === 'professional' ? '专业工作流' : '标准生成' }}</span>
              <span>{{ task.workflowCost || task.pointsCost || qualityCost(task.quality) }} 额度</span>
            </article>
          </TransitionGroup>
        </section>

        <section v-reveal="230" class="results-section">
          <div class="block-head results-head">
            <div>
              <h2>结果画廊</h2>
              <p>{{ doneTasks.length ? `已生成 ${doneTasks.length} 张图片` : '生成完成后会自动进入画廊' }}</p>
            </div>
            <div class="view-toggle" aria-hidden="true">
              <span>网格</span>
              <span>列表</span>
            </div>
          </div>

          <div v-if="tasksStore.tasks.length === 0" class="gallery-empty surface-card">
            <h1>创作画布</h1>
            <p>选择模式、工作流、质量和尺寸，然后描述你要生成的画面。</p>
          </div>

          <TransitionGroup v-else name="list" tag="div" class="gallery-grid">
            <TaskCard
              v-for="task in sortedTasks"
              :key="task.id"
              :task="task"
              @remove="tasksStore.removeTask(task.id)"
            />
          </TransitionGroup>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onMounted, ref } from 'vue'
import { ElMessage } from '../services/toast'
import TaskCard from '../components/TaskCard.vue'
import { IMAGE_SIZE_GROUPS, formatImageSize } from '../constants/imageSizes'
import { useTasksStore } from '../stores/tasks'
import { fetchPlansConfig, readCachedPlans } from '../services/plansCache'

defineOptions({ name: 'Home' })

const tasksStore = useTasksStore()

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
    description: '日常创作，低/中质量优先使用体验积分',
    costs: { low: 1, medium: 2, high: 3 },
    uses_experience_points: true
  },
  {
    workflow_type: 'professional',
    workflow_preset: 'pro-detail',
    name: '专业工作流',
    description: '更强稳定性与细节控制，仅消耗订阅额度',
    costs: { low: 1, medium: 2, high: 3 },
    uses_experience_points: false
  }
])
const refImage = ref(null)
const refPreview = ref('')
const fileInput = ref(null)
const promptInput = ref(null)

const modes = [
  { label: '文生图', value: 'text2img', icon: '□' },
  { label: '参考图', value: 'ref2img', icon: '▧' },
  { label: '编辑', value: 'edit', icon: '✕' }
]

const fallbackQualities = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' }
]

const promptExamples = [
  '未来主义城市，晨雾穿过玻璃建筑，清晨自然光，广角镜头，画面干净',
  '山间湖泊，日出，薄雾，超写实摄影，柔和色彩，宁静构图',
  '极简产品摄影，白色陶瓷杯，柔光，浅景深，杂志级构图'
]

const qualities = ref(fallbackQualities)
const sizeGroups = ref(IMAGE_SIZE_GROUPS)

const needImage = computed(() => mode.value !== 'text2img')
const imageInputTitle = computed(() => (mode.value === 'edit' ? '原图' : '参考图'))
const imageInputHint = computed(() => (mode.value === 'edit' ? '点击上传需要编辑的原图' : '点击上传参考图'))
const imageInputAction = computed(() => {
  if (refPreview.value) return '更换图片'
  return mode.value === 'edit' ? '上传原图' : '上传参考图'
})
const canSubmit = computed(() => {
  if (needImage.value) return Boolean(prompt.value.trim() && refImage.value)
  return Boolean(prompt.value.trim())
})
const sortedTasks = computed(() => [...tasksStore.tasks].reverse())
const recentTasks = computed(() => sortedTasks.value.slice(0, 5))
const activeTaskCount = computed(() => tasksStore.tasks.filter((task) => ['queued', 'generating'].includes(task.status)).length)
const doneTasks = computed(() => tasksStore.tasks.filter((task) => task.status === 'done'))
const selectedWorkflow = computed(() => {
  return workflowOptions.value.find(
    (item) =>
      item.workflow_type === selectedWorkflowType.value &&
      (item.workflow_preset || '') === selectedWorkflowPreset.value
  ) || workflowOptions.value.find((item) => item.workflow_type === selectedWorkflowType.value) || workflowOptions.value[0]
})
const selectedSizeGroup = computed(() => {
  return sizeGroups.value.find((group) => group.ratio === selectedRatio.value) || sizeGroups.value[0]
})
const availableSizes = computed(() => selectedSizeGroup.value?.sizes || [])
const currentCost = computed(() => qualityCost(quality.value))
const qualitySource = computed(() => {
  if (selectedWorkflow.value?.uses_experience_points && quality.value !== 'high') {
    return '优先体验积分'
  }
  return '订阅额度'
})
const workflowSummary = computed(() => {
  const workflowName = selectedWorkflow.value?.name || '标准生成'
  return `${workflowName} · ${qualityLabel(quality.value)} · ${formatImageSize(size.value)}`
})
const placeholder = computed(() => {
  if (mode.value === 'text2img') return '描述画面、主体、风格、光线与构图。例：清晨湖边的极简建筑，柔和自然光，画面安静。'
  if (mode.value === 'ref2img') return '结合参考图说明想保留什么、改变什么。'
  return '描述要如何编辑原图，例如替换背景、调整风格或修复细节。'
})

onMounted(() => {
  applyPlansConfig(readCachedPlans())
  fetchWorkflowOptions()
})

onActivated(() => {
  tasksStore.fetchTasks().catch(() => {
    tasksStore.resumePolling()
  })
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
    applyPlansConfig(await fetchPlansConfig())
  } catch (_) {}
}

function applyPlansConfig(data) {
  if (!data) return
  const presets = data.workflow_presets
  const generationOptions = data.generation_options
    if (Array.isArray(presets) && presets.length) {
      workflowOptions.value = presets
      if (!presets.some((item) => item.workflow_type === selectedWorkflowType.value)) {
        selectWorkflow(presets[0])
      }
    }
    if (Array.isArray(generationOptions?.qualities) && generationOptions.qualities.length) {
      qualities.value = generationOptions.qualities.map((item) => ({
        ...item,
        label: item.label?.replace('质量', '') || item.value
      }))
      if (!qualities.value.some((item) => item.value === quality.value)) {
        quality.value = qualities.value[0].value
      }
    }
    if (Array.isArray(generationOptions?.image_size_groups) && generationOptions.image_size_groups.length) {
      sizeGroups.value = generationOptions.image_size_groups
      ensureValidSizeSelection()
    }
}

function selectWorkflow(item) {
  selectedWorkflowType.value = item.workflow_type
  selectedWorkflowPreset.value = item.workflow_preset || ''
}

function isWorkflowActive(item) {
  return item.workflow_type === selectedWorkflowType.value && (item.workflow_preset || '') === selectedWorkflowPreset.value
}

function workflowMark(type) {
  return type === 'professional' ? '✣' : '□'
}

function workflowBillingText(item) {
  if (item.uses_experience_points) return '低/中质量优先使用体验积分'
  return '仅消耗订阅额度'
}

function qualityCost(value) {
  return selectedWorkflow.value?.costs?.[value] ?? 0
}

function qualityLabel(value) {
  const item = qualities.value.find((qualityItem) => qualityItem.value === value)
  const fallback = { low: '低质量', medium: '中质量', high: '高质量' }
  if (item?.label) return item.label.includes('质量') ? item.label : `${item.label}质量`
  return fallback[value] || value
}

function statusLabel(status) {
  const map = {
    queued: '排队中',
    generating: '生成中',
    done: '成功',
    failed: '失败（已退款）'
  }
  return map[status] || status
}

function selectRatio(ratio) {
  selectedRatio.value = ratio
  const group = sizeGroups.value.find((item) => item.ratio === ratio)
  if (group && !group.sizes.some((item) => item.value === size.value)) {
    size.value = group.sizes[0].value
  }
}

function ensureValidSizeSelection() {
  const currentGroup = sizeGroups.value.find((group) =>
    group.sizes.some((item) => item.value === size.value)
  )
  if (currentGroup) {
    selectedRatio.value = currentGroup.ratio
    return
  }

  const defaultGroup = sizeGroups.value.find((group) => group.ratio === '1:1') || sizeGroups.value[0]
  selectedRatio.value = defaultGroup?.ratio || '1:1'
  size.value = defaultGroup?.sizes?.[0]?.value || '1024x1024'
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

function clearPrompt() {
  prompt.value = ''
  nextTick(() => promptInput.value?.focus())
}

function fillPromptExample() {
  prompt.value = promptExamples[Math.floor(Math.random() * promptExamples.length)]
  nextTick(() => promptInput.value?.focus())
}

function polishPrompt() {
  if (!prompt.value.trim()) {
    fillPromptExample()
    return
  }
  if (!/[，。,.]/.test(prompt.value)) {
    prompt.value = `${prompt.value}，画面干净，光线自然，细节清晰，构图稳定`
  }
}

function focusPanel() {
  document.querySelector('.tool-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
.studio-shell {
  max-width: 1480px;
  margin: 0 auto;
  padding: 28px 28px 96px;
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 28px;
}

.tool-panel {
  position: sticky;
  top: 92px;
  align-self: start;
  min-width: 0;
  overflow: hidden;
  padding: 24px;
  transform-origin: 20% 0;
}

.panel-section + .panel-section {
  margin-top: 25px;
}

.section-title {
  margin-bottom: 12px;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 850;
}

.mode-grid,
.choice-grid {
  display: grid;
  gap: 9px;
}

.mode-grid {
  grid-template-columns: repeat(3, 1fr);
}

.choice-grid.three {
  grid-template-columns: repeat(3, 1fr);
}

.mode-button,
.choice-card,
.workflow-card,
.resolution-button,
.ratio-pill,
.upload-card,
.prompt-actions button,
.tune-button,
.block-head button {
  border: 1px solid var(--color-line);
  background: rgba(255, 255, 255, 0.7);
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  transform: translateZ(0);
  transition:
    border-color var(--transition-base),
    background var(--transition-base),
    color var(--transition-base),
    transform var(--transition-base),
    box-shadow var(--transition-base);
}

.mode-button {
  min-height: 46px;
  display: grid;
  place-items: center;
  gap: 2px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 800;
}

.mode-button span {
  color: var(--color-blue);
  font-size: 14px;
  transition: transform var(--transition-base), color var(--transition-base);
}

.mode-button.active,
.choice-card.active,
.workflow-card.active,
.resolution-button.active,
.ratio-pill.active {
  border-color: var(--color-blue);
  background: rgba(60, 110, 232, 0.07);
  box-shadow: 0 0 0 1px rgba(60, 110, 232, 0.1);
  transform: translateY(-1px);
}

.mode-button.active span {
  transform: translateY(-1px) rotate(-6deg);
}

.workflow-list {
  display: grid;
  gap: 10px;
}

.workflow-card {
  width: 100%;
  min-height: 68px;
  padding: 12px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  border-radius: var(--radius-md);
  text-align: left;
}

.workflow-mark {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-paper-soft);
  color: var(--color-ink);
  font-weight: 900;
  transition: background var(--transition-base), color var(--transition-base), transform var(--transition-base);
}

.workflow-card.active .workflow-mark,
.workflow-card:hover .workflow-mark {
  background: var(--color-blue);
  color: #fff;
  transform: rotate(-8deg) scale(1.04);
}

.workflow-copy {
  display: grid;
  gap: 2px;
}

.workflow-copy strong {
  color: var(--color-ink);
  font-size: 13px;
}

.workflow-copy small {
  color: var(--color-muted);
  font-size: 11px;
  line-height: 1.35;
}

.workflow-arrow {
  color: var(--color-blue);
  font-size: 18px;
  transition: transform var(--transition-base);
}

.workflow-card:hover .workflow-arrow {
  transform: translateX(3px);
}

.workflow-detail {
  margin-top: 12px;
  padding: 12px;
  display: grid;
  gap: 8px;
  border: 1px solid rgba(60, 110, 232, 0.18);
  border-radius: var(--radius-md);
  background: rgba(60, 110, 232, 0.045);
  animation: detail-in 380ms var(--ease-out-soft) both;
}

.workflow-detail div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
}

.workflow-detail strong {
  color: var(--color-ink);
}

.choice-card {
  min-height: 48px;
  padding: 9px;
  display: grid;
  gap: 2px;
  border-radius: var(--radius-md);
  text-align: center;
}

.choice-card strong {
  font-size: 15px;
}

.choice-card span {
  color: var(--color-muted);
  font-size: 11px;
}

.ratio-scroll {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  overscroll-behavior-inline: contain;
  padding-bottom: 4px;
}

.ratio-pill {
  flex: 0 0 auto;
  min-width: 68px;
  padding: 8px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.resolution-list {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.resolution-button {
  min-height: 42px;
  padding: 8px 11px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  border-radius: var(--radius-md);
  color: var(--color-muted);
  font-size: 12px;
}

.resolution-button strong {
  color: var(--color-blue);
  font-size: 12px;
}

.upload-card {
  width: 100%;
  min-height: 96px;
  padding: 10px;
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 12px;
  border-style: dashed;
  border-radius: var(--radius-md);
  text-align: left;
}

.upload-card img {
  width: 76px;
  height: 76px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  animation: image-pop 360ms var(--ease-out-soft) both;
}

.upload-placeholder {
  color: var(--color-soft);
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.6;
}

.upload-card strong {
  color: var(--color-ink);
  font-size: 12px;
}

.studio-main {
  min-width: 0;
  display: grid;
  gap: 22px;
}

.prompt-card {
  padding: 22px;
  overflow: hidden;
}

.prompt-head,
.prompt-actions,
.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.prompt-head {
  margin-bottom: 10px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 800;
}

.prompt-input {
  width: 100%;
  min-height: 150px;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  resize: vertical;
  background: rgba(255, 255, 255, 0.8);
  color: var(--color-ink);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.8;
  outline: none;
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base),
    background var(--transition-base),
    transform var(--transition-base);
}

.prompt-input::placeholder {
  color: #949991;
}

.prompt-input:focus {
  border-color: var(--color-blue);
  box-shadow: 0 0 0 4px rgba(60, 110, 232, 0.08);
  background: rgba(255, 255, 255, 0.92);
  transform: translateY(-1px);
}

.prompt-actions {
  margin-top: 12px;
}

.quick-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.prompt-actions button,
.block-head button,
.tune-button {
  min-height: 34px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 800;
}

.cost-note {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
}

.generate-bar {
  padding: 10px;
  display: grid;
  grid-template-columns: 1fr 74px;
  gap: 10px;
  align-items: center;
  transform-origin: center;
}

.generate-button {
  min-height: 54px;
  font-family: var(--font-ui);
  font-size: 16px;
  font-weight: 850;
  isolation: isolate;
}

.generate-button:not(:disabled)::after {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: inherit;
  background: linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, 0.18) 45%, transparent 62%);
  opacity: 0;
  transform: translateX(-36%);
  transition: opacity var(--transition-base), transform 620ms var(--ease-out-soft);
}

.generate-button:hover:not(:disabled)::after {
  opacity: 1;
  transform: translateX(36%);
}

.tune-button {
  height: 54px;
  border-radius: var(--radius-md);
  color: var(--color-ink);
}

.task-log {
  padding: 20px;
}

.block-head {
  margin-bottom: 14px;
}

.block-head h2 {
  margin: 0;
  font-size: 18px;
}

.block-head p {
  margin: 4px 0 0;
  color: var(--color-muted);
  font-size: 12px;
}

.empty-log,
.gallery-empty {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 13px;
}

.empty-log {
  padding: 16px;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-md);
}

.log-list {
  display: grid;
  gap: 2px;
  position: relative;
}

.log-row {
  min-height: 45px;
  display: grid;
  grid-template-columns: auto minmax(220px, 1fr) 88px 112px 78px;
  align-items: center;
  gap: 14px;
  border-bottom: 1px solid rgba(226, 229, 223, 0.7);
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  border-radius: var(--radius-sm);
  transition:
    background var(--transition-base),
    transform var(--transition-base),
    box-shadow var(--transition-base);
}

.log-row:hover {
  background: rgba(255, 255, 255, 0.62);
  box-shadow: inset 0 0 0 1px rgba(226, 229, 223, 0.76);
  transform: translateX(3px);
}

.log-row:last-child {
  border-bottom: 0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-blue);
}

.status-done {
  background: var(--color-green);
}

.status-failed {
  background: var(--color-red);
}

.status-generating {
  animation: pulse-dot 1.1s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { transform: scale(1); opacity: 0.62; }
  50% { transform: scale(1.55); opacity: 1; }
}

.log-prompt {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
}

.log-prompt strong {
  color: var(--color-ink);
}

.log-prompt span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.results-head {
  margin-bottom: 14px;
}

.view-toggle {
  display: inline-flex;
  gap: 6px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
}

.view-toggle span {
  padding: 6px 9px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.58);
}

.gallery-empty {
  min-height: 230px;
  display: grid;
  place-items: center;
  text-align: center;
  animation: gallery-breathe 4.8s ease-in-out infinite;
}

.gallery-empty h1 {
  margin: 0 0 8px;
  font-size: 30px;
}

.gallery-empty p {
  margin: 0;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px;
  position: relative;
}

@media (prefers-reduced-motion: reduce) {
  .status-generating {
    animation: none;
  }

  .mode-button,
  .choice-card,
  .workflow-card,
  .resolution-button,
  .ratio-pill,
  .upload-card,
  .prompt-actions button,
  .tune-button,
  .block-head button {
    transition: none;
  }
}

.mode-button:hover,
.choice-card:hover,
.workflow-card:hover,
.resolution-button:hover,
.ratio-pill:hover,
.upload-card:hover,
.prompt-actions button:hover,
.tune-button:hover,
.block-head button:hover {
  transform: translateY(-1px);
  border-color: var(--color-line-strong);
  box-shadow: 0 12px 28px rgba(23, 23, 23, 0.07);
}

.mode-button:active,
.choice-card:active,
.workflow-card:active,
.resolution-button:active,
.ratio-pill:active,
.upload-card:active,
.prompt-actions button:active,
.tune-button:active,
.block-head button:active {
  transform: translateY(0) scale(0.985);
}

@media (max-width: 1180px) {
  .studio-shell {
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 20px;
    padding: 22px 18px 94px;
  }

  .tool-panel {
    padding: 18px;
  }

  .log-row {
    grid-template-columns: auto minmax(170px, 1fr) 70px 90px 64px;
  }
}

@keyframes detail-in {
  from {
    opacity: 0;
    transform: translate3d(0, 8px, 0) scale(0.98);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
  }
}

@keyframes image-pop {
  from {
    opacity: 0;
    transform: scale(0.92);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes gallery-breathe {
  0%, 100% {
    box-shadow: var(--shadow-sm);
  }

  50% {
    box-shadow: 0 22px 60px rgba(60, 110, 232, 0.09);
  }
}

@media (max-width: 900px) {
  .studio-shell {
    grid-template-columns: 1fr;
  }

  .tool-panel {
    position: static;
  }

  .resolution-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .studio-shell {
    padding: 14px 12px 92px;
    gap: 14px;
  }

  .tool-panel,
  .prompt-card,
  .task-log {
    border-radius: 20px;
  }

  .mode-grid,
  .choice-grid.three,
  .resolution-list,
  .generate-bar {
    grid-template-columns: 1fr;
  }

  .prompt-actions,
  .block-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .log-row {
    grid-template-columns: auto minmax(0, 1fr);
    gap: 8px 10px;
    padding: 10px 0;
  }

  .log-row > span:not(.status-dot) {
    display: none;
  }

  .gallery-grid {
    grid-template-columns: 1fr;
  }
}
</style>
