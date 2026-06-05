<template>
  <div class="home-page">
    <NavBar />

    <div class="studio-container">
      <div class="command-panel">
        <div class="command-inner">
          <div class="command-mode">
            <button v-for="m in modeDefs" :key="m.value"
              :class="['cmd-mode-btn', { active: mode === m.value }]"
              @click="switchMode(m.value)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon v-if="m.value === 'text2img'" points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                <template v-else-if="m.value === 'ref2img'">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </template>
                <template v-else>
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                </template>
              </svg>
              <span class="cmd-mode-label">{{ m.label }}</span>
            </button>
          </div>

          <Transition name="upload">
            <div v-if="needImage" class="command-upload" @click="triggerUpload">
            <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" class="hidden-input" @change="handleFileSelect" />
            <template v-if="refPreview">
              <img :src="refPreview" class="cmd-upload-thumb" />
              <span class="cmd-upload-change">换图</span>
            </template>
            <template v-else>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              <span class="cmd-upload-text">上传图片</span>
            </template>
          </div>
          </Transition>

          <div class="command-input-wrap" :class="{ 'has-text': prompt }">
            <textarea
              v-model="prompt"
              class="command-input"
              :placeholder="''"
              :rows="1"
              ref="promptInput"
              @input="autoResize"
              @keydown.enter.exact.prevent="handleSubmit"
            ></textarea>
            <Transition name="hint" mode="out-in">
              <span v-if="!prompt" :key="promptHint" class="cmd-placeholder">{{ promptHint }}</span>
            </Transition>
          </div>

          <div class="command-quality">
            <button v-for="q in qualityOpts" :key="q.value"
              :class="['cmd-q-btn', { active: quality === q.value }]"
              @click="quality = q.value"
            >{{ q.label }}</button>
          </div>

          <div class="command-size">
            <div class="cmd-dropdown" :class="{ open: aspectOpen }">
              <button class="cmd-select cmd-select--aspect" @click.stop="toggleAspect">
                {{ aspect }}
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9" /></svg>
              </button>
              <Teleport to="body">
                <Transition name="drop">
                  <div v-if="aspectOpen" class="cmd-drop-panel" :style="aspectPanelStyle">
                    <button v-for="a in aspectOpts" :key="a.value"
                      :class="['cmd-drop-opt', { active: aspect === a.value }]"
                      @click.stop="selectAspect(a.value)">
                      <span class="opt-ratio">{{ a.label }}</span>
                      <span class="opt-desc">{{ aspectDesc(a.value) }}</span>
                    </button>
                  </div>
                </Transition>
              </Teleport>
            </div>
            <div class="cmd-dropdown" :class="{ open: sizeOpen }">
              <button class="cmd-select" @click.stop="toggleSize">
                {{ sizeLabel }}
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9" /></svg>
              </button>
              <Teleport to="body">
                <Transition name="drop">
                  <div v-if="sizeOpen" class="cmd-drop-panel" :style="sizePanelStyle">
                    <button v-for="s in currentSizes" :key="s.value"
                      :class="['cmd-drop-opt', { active: size === s.value }]"
                      @click.stop="selectSize(s.value)">
                      <span class="opt-size">{{ s.label }}</span>
                    </button>
                  </div>
                </Transition>
              </Teleport>
            </div>
          </div>

          <button class="cmd-fire" :disabled="!canSubmit" @click="handleSubmit">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </button>
        </div>
      </div>

      <div v-if="tasksStore.tasks.length === 0" class="empty-studio">
        <div class="empty-graphic">
          <div class="empty-frame frame-1"></div>
          <div class="empty-frame frame-2"></div>
          <div class="empty-frame frame-3"></div>
        </div>
        <h2 class="empty-title">创作画布</h2>
        <p class="empty-desc">在上方输入你的第一个提示词，开始创作</p>
      </div>

      <div v-else class="gallery-grid">
        <TransitionGroup name="gallery">
          <TaskCard
            v-for="task in sortedTasks"
            :key="task.id"
            :task="task"
            @remove="tasksStore.removeTask(task.id)"
          />
        </TransitionGroup>
      </div>

      <div v-if="completedCount > 0" class="gallery-actions">
        <button class="btn-clear" @click="tasksStore.clearCompleted()">
          清空已完成 ({{ completedCount }})
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../components/NavBar.vue'
import TaskCard from '../components/TaskCard.vue'
import { useTasksStore } from '../stores/tasks'
import { useUserStore } from '../stores/user'

const tasksStore = useTasksStore()
const userStore = useUserStore()

const mode = ref('text2img')
const prompt = ref('')
const quality = ref('low')
const aspect = ref('1:1')
const size = ref('1024x1024')
const refImage = ref(null)
const refPreview = ref('')
const fileInput = ref(null)
const promptInput = ref(null)

const modeDefs = [
  { label: '文生图', value: 'text2img' },
  { label: '参考图', value: 'ref2img' },
  { label: '编辑', value: 'edit' },
]

const qualityOpts = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
]

const aspectOpts = [
  { label: '21:9', value: '21:9' }, { label: '16:9', value: '16:9' },
  { label: '3:2', value: '3:2' }, { label: '4:3', value: '4:3' },
  { label: '1:1', value: '1:1' }, { label: '3:4', value: '3:4' },
  { label: '2:3', value: '2:3' }, { label: '9:16', value: '9:16' },
]

const sizeMap = {
  '21:9': [{ label: '2688×1152', value: '2688x1152' }, { label: '3360×1440', value: '3360x1440' }],
  '16:9': [{ label: '1344×768', value: '1344x768' }, { label: '2688×1536', value: '2688x1536' }, { label: '3840×2160', value: '3840x2160' }],
  '3:2': [{ label: '1536×1024', value: '1536x1024' }, { label: '2304×1536', value: '2304x1536' }, { label: '3072×2048', value: '3072x2048' }],
  '4:3': [{ label: '1152×896', value: '1152x896' }, { label: '2304×1792', value: '2304x1792' }],
  '1:1': [{ label: '1024', value: '1024x1024' }, { label: '2048', value: '2048x2048' }],
  '3:4': [{ label: '896×1152', value: '896x1152' }, { label: '1792×2304', value: '1792x2304' }],
  '2:3': [{ label: '1024×1536', value: '1024x1536' }, { label: '1536×2304', value: '1536x2304' }, { label: '2048×3072', value: '2048x3072' }],
  '9:16': [{ label: '720×1280', value: '720x1280' }, { label: '1440×2560', value: '1440x2560' }, { label: '2160×3840', value: '2160x3840' }],
}

const needImage = computed(() => mode.value !== 'text2img')
const canSubmit = computed(() => {
  if (needImage.value) return prompt.value.trim() && refImage.value
  return prompt.value.trim()
})
const promptHint = computed(() => {
  if (mode.value === 'text2img') return '描述你想生成的画面… (Enter 发送)'
  if (mode.value === 'ref2img') return '参考图片 + 描述生成什么… (Enter 发送)'
  return '描述修改方式… (Enter 发送)'
})
const currentSizes = computed(() => sizeMap[aspect.value] || sizeMap['1:1'])
const sizeLabel = computed(() => {
  const match = currentSizes.value.find((s) => s.value === size.value)
  return match?.label || size.value
})
const sortedTasks = computed(() => [...tasksStore.tasks].reverse())
const completedCount = computed(() => tasksStore.tasks.filter(t => t.status === 'done' || t.status === 'failed').length)

const aspectOpen = ref(false)
const sizeOpen = ref(false)

const ratioDescMap = {
  '21:9': '超宽', '16:9': '宽屏', '3:2': '横屏',
  '4:3': '标准', '1:1': '正方', '3:4': '竖屏',
  '2:3': '竖屏', '9:16': '手机',
}
function aspectDesc(v) { return ratioDescMap[v] || '' }

const aspectPanelStyle = computed(() => {
  if (!aspectOpen.value) return {}
  const rect = document.querySelector('.cmd-select--aspect')?.getBoundingClientRect()
  if (!rect) return {}
  return { position: 'fixed', top: rect.bottom + 4 + 'px', left: rect.left + 'px', minWidth: rect.width + 'px' }
})
const sizePanelStyle = computed(() => {
  if (!sizeOpen.value) return {}
  const rect = document.querySelector('.command-size .cmd-select:not(.cmd-select--aspect)')?.getBoundingClientRect()
  if (!rect) return {}
  return { position: 'fixed', top: rect.bottom + 4 + 'px', left: rect.left + 'px', minWidth: rect.width + 'px' }
})

function selectAspect(v) {
  aspect.value = v
  aspectOpen.value = false
  sizeOpen.value = false
}
function selectSize(v) {
  size.value = v
  sizeOpen.value = false
  aspectOpen.value = false
}

function toggleAspect() {
  sizeOpen.value = false
  aspectOpen.value = !aspectOpen.value
}
function toggleSize() {
  aspectOpen.value = false
  sizeOpen.value = !sizeOpen.value
}

function closeDropdowns() {
  aspectOpen.value = false
  sizeOpen.value = false
}
function handleDocClick(e) {
  const target = e.target
  if (!target.closest('.cmd-dropdown') && !target.closest('.cmd-drop-panel')) closeDropdowns()
}

onMounted(() => document.addEventListener('click', handleDocClick, true))
onBeforeUnmount(() => document.removeEventListener('click', handleDocClick, true))

watch(aspect, (v) => {
  const first = sizeMap[v]?.[0]?.value
  if (first) size.value = first
})

function switchMode(v) {
  mode.value = v
  if (v === 'text2img') {
    refImage.value = null
    refPreview.value = ''
  }
  nextTick(() => {
    promptInput.value?.focus()
    autoResize()
  })
}

function autoResize() {
  const el = promptInput.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

function triggerUpload() { fileInput.value?.click() }

function handleFileSelect(e) {
  const f = e.target.files[0]
  if (f) setFile(f)
}
function setFile(f) {
  if (!f.type.match(/image\/(png|jpeg|webp)/)) {
    ElMessage.warning('仅支持 PNG / JPG / WebP')
    return
  }
  refImage.value = f
  const r = new FileReader()
  r.onload = (ev) => { refPreview.value = ev.target.result }
  r.readAsDataURL(f)
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
  })

  prompt.value = ''
  if (mode.value === 'text2img') {
    refImage.value = null
    refPreview.value = ''
  }
  nextTick(() => {
    promptInput.value?.focus()
    autoResize()
  })
}

onMounted(() => userStore.fetchUserInfo())
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background:
    radial-gradient(ellipse at 20% 50%, rgba(106, 155, 204, 0.04) 0%, transparent 60%),
    radial-gradient(ellipse at 80% 30%, rgba(217, 119, 87, 0.03) 0%, transparent 50%),
    var(--color-dark);
}

.studio-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 24px 60px;
}

.command-panel {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 12px 0 20px;
  background:
    linear-gradient(180deg, var(--color-dark) 60%, transparent);
  backdrop-filter: blur(12px);
  animation: panel-slide 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
  animation-delay: 0.1s;
}

@keyframes panel-slide {
  from {
    opacity: 0;
    transform: translateY(-12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.command-inner {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(232, 230, 220, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.09);
  border-radius: var(--radius-xl);
  backdrop-filter: blur(20px);
  transition: border-color 0.3s ease, box-shadow 0.3s ease, padding 0.25s ease;
}

.command-inner:focus-within {
  border-color: rgba(217, 119, 87, 0.25);
  box-shadow: 0 0 30px rgba(217, 119, 87, 0.06);
  padding: 12px 10px;
}

.command-mode {
  display: flex;
  gap: 3px;
  padding: 3px;
  background: rgba(250, 249, 245, 0.03);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.cmd-mode-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 12px;
  background: transparent;
  border: none;
  border-radius: calc(var(--radius-md) - 2px);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  white-space: nowrap;
  position: relative;
}

.cmd-mode-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: rgba(217, 119, 87, 0.12);
  opacity: 0;
  transform: scale(0.8);
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.cmd-mode-btn:hover { color: var(--color-light); }
.cmd-mode-btn:hover::after { opacity: 0.4; transform: scale(1); }

.cmd-mode-btn.active {
  color: var(--color-orange);
}
.cmd-mode-btn.active::after {
  opacity: 1;
  transform: scale(1);
}

.command-upload {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1px dashed rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-mid);
  flex-shrink: 0;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}

.upload-enter-active {
  animation: upload-appear 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}
.upload-leave-active {
  animation: upload-appear 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94) both reverse;
}

@keyframes upload-appear {
  from {
    opacity: 0;
    transform: scale(0.92);
    max-width: 0;
    padding-left: 0;
    padding-right: 0;
    margin-right: -8px;
  }
  to {
    opacity: 1;
    transform: scale(1);
    max-width: 200px;
    padding-left: 12px;
    padding-right: 12px;
    margin-right: 0;
  }
}

.command-upload:hover {
  border-color: rgba(106, 155, 204, 0.3);
  color: var(--color-blue);
}

.cmd-upload-thumb {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  object-fit: cover;
}

.cmd-upload-change {
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 600;
}

.cmd-upload-text {
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
}

.hidden-input { display: none; }

.command-input-wrap {
  flex: 1;
  min-width: 0;
  position: relative;
}

.command-input {
  width: 100%;
  display: block;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-light);
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.55;
  outline: none;
  resize: none;
  overflow: hidden;
  min-height: 38px;
  transition: background 0.25s ease, border-color 0.25s ease;
}

.command-input-wrap.has-text .command-input {
  background: rgba(250, 249, 245, 0.025);
}

.cmd-placeholder {
  position: absolute;
  top: 8px;
  left: 12px;
  right: 12px;
  pointer-events: none;
  user-select: none;
  color: var(--color-mid);
  opacity: 0.4;
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.55;
  font-style: italic;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hint-enter-active,
.hint-leave-active {
  transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.hint-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.hint-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.command-quality {
  display: flex;
  gap: 3px;
  flex-shrink: 0;
}

.cmd-q-btn {
  padding: 7px 12px;
  background: rgba(250, 249, 245, 0.03);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
}

.cmd-q-btn:hover {
  border-color: rgba(232, 230, 220, 0.12);
  color: var(--color-light);
  transform: translateY(-1px);
}

.cmd-q-btn.active {
  background: rgba(217, 119, 87, 0.08);
  border-color: rgba(217, 119, 87, 0.2);
  color: var(--color-orange);
  transform: translateY(0);
}

.command-size {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.cmd-dropdown {
  position: relative;
}

.cmd-select {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 8px;
  background: rgba(250, 249, 245, 0.03);
  border: 1px solid rgba(232, 230, 220, 0.08);
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
  outline: none;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  white-space: nowrap;
}

.cmd-select:hover {
  border-color: rgba(232, 230, 220, 0.2);
  background: rgba(250, 249, 245, 0.05);
}

.cmd-select--aspect {
  color: var(--color-green);
}

.cmd-dropdown.open .cmd-select {
  border-color: rgba(106, 155, 204, 0.3);
  background: rgba(250, 249, 245, 0.06);
}

.cmd-drop-panel {
  position: fixed;
  z-index: 1000;
  padding: 6px;
  background: #1a1a18;
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-lg);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(250, 249, 245, 0.04);
  backdrop-filter: blur(20px);
  display: flex;
  flex-direction: column;
  gap: 2px;
  transform-origin: top left;
}

.drop-enter-active {
  animation: drop-in 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.drop-leave-active {
  animation: drop-in 0.15s cubic-bezier(0.25, 0.46, 0.45, 0.94) reverse;
  pointer-events: none;
}

@keyframes drop-in {
  from {
    opacity: 0;
    transform: translateY(-6px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.cmd-drop-opt {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  white-space: nowrap;
}

.cmd-drop-opt:hover {
  background: rgba(232, 230, 220, 0.06);
  color: var(--color-light);
}

.cmd-drop-opt.active {
  background: rgba(106, 155, 204, 0.1);
  color: var(--color-blue);
}

.opt-ratio {
  font-weight: 700;
  min-width: 40px;
  color: var(--color-green);
}

.cmd-drop-opt.active .opt-ratio {
  color: var(--color-blue);
}

.opt-desc {
  font-size: 11px;
  opacity: 0.5;
}

.opt-size {
  font-weight: 600;
}

.cmd-fire {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  background: var(--color-orange);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-dark);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.cmd-fire:hover:not(:disabled) {
  background: #c8694a;
  transform: scale(1.08);
  box-shadow: 0 0 24px rgba(217, 119, 87, 0.35);
}

.cmd-fire:not(:disabled):active {
  transform: scale(0.94);
  transition: all 0.1s ease;
}

.cmd-fire:disabled {
  opacity: 0.25;
  cursor: not-allowed;
  transform: scale(1);
}

.empty-studio {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  animation: empty-enter 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
  animation-delay: 0.3s;
}

@keyframes empty-enter {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.empty-graphic {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.empty-frame {
  width: 48px;
  height: 60px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(232, 230, 220, 0.06);
  background: rgba(232, 230, 220, 0.02);
  animation: empty-float 4s ease-in-out infinite;
}

.frame-1 { animation-delay: 0s; }
.frame-2 {
  animation-delay: 0.5s;
  border-color: rgba(217, 119, 87, 0.08);
  background: rgba(217, 119, 87, 0.02);
}
.frame-3 {
  animation-delay: 1s;
  border-color: rgba(106, 155, 204, 0.08);
  background: rgba(106, 155, 204, 0.02);
}

@keyframes empty-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.empty-title {
  font-size: 28px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, var(--color-light) 0%, var(--color-orange) 60%, var(--color-blue) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.empty-desc {
  font-family: var(--font-body);
  font-size: 16px;
  color: var(--color-mid);
  font-style: italic;
  opacity: 0.6;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 18px;
  padding-top: 8px;
  animation: gallery-enter 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

@keyframes gallery-enter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.gallery-grid > * {
  animation: card-rise 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}
.gallery-grid > *:nth-child(1) { animation-delay: 0s; }
.gallery-grid > *:nth-child(2) { animation-delay: 0.06s; }
.gallery-grid > *:nth-child(3) { animation-delay: 0.12s; }
.gallery-grid > *:nth-child(4) { animation-delay: 0.18s; }
.gallery-grid > *:nth-child(5) { animation-delay: 0.24s; }
.gallery-grid > *:nth-child(n+6) { animation-delay: 0.3s; }

@keyframes card-rise {
  from {
    opacity: 0;
    transform: translateY(28px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.gallery-actions {
  display: flex;
  justify-content: center;
  padding: 32px 0;
}

.btn-clear {
  padding: 10px 24px;
  background: transparent;
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
}

.btn-clear:hover {
  border-color: rgba(232, 230, 220, 0.25);
  color: var(--color-light);
}

.gallery-enter-active,
.gallery-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.gallery-enter-from {
  opacity: 0;
  transform: translateY(30px) scale(0.92);
}

.gallery-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.gallery-move {
  transition: transform 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

@media (max-width: 768px) {
  .studio-container { padding: 16px 12px 40px; }
  .command-inner {
    flex-wrap: wrap;
    gap: 6px;
  }
  .command-quality { order: 1; }
  .command-size { order: 2; }
  .command-fire { order: 3; }
  .gallery-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 10px;
  }
}
</style>
