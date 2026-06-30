<template>
  <Teleport to="body">
    <div v-if="open" class="local-edit-backdrop" @mousedown.self="handleClose">
      <section class="local-edit-dialog" role="dialog" aria-modal="true" aria-label="局部修改">
        <header class="local-edit-header">
          <div>
            <strong>局部修改</strong>
            <span>{{ itemTitle }}</span>
          </div>
          <button type="button" title="关闭" :disabled="busy || preparingMask" @click="handleClose">
            <X :size="18" />
          </button>
        </header>

        <div class="local-edit-body">
          <div class="local-edit-stage-shell">
            <div v-if="imageUrl && !imageError" class="local-edit-stage">
              <img
                ref="imageRef"
                :src="imageUrl"
                :alt="itemTitle"
                draggable="false"
                @load="syncImageElement"
                @error="handleImageError"
              />
              <canvas
                ref="maskCanvas"
                class="local-edit-mask-canvas"
                :class="{ disabled: !imageReady || busy || preparingMask }"
                @pointerdown="startStroke"
                @pointermove="continueStroke"
                @pointerup="finishStroke"
                @pointercancel="finishStroke"
                @pointerleave="finishStroke"
              ></canvas>
            </div>
            <div v-else class="local-edit-image-error">
              <ImageOff :size="28" />
              <span>图片无法载入</span>
            </div>
          </div>

          <aside class="local-edit-controls">
            <div class="local-edit-tool-row" role="group" aria-label="遮罩工具">
              <button type="button" title="画笔" :class="{ active: tool === 'brush' }" @click="tool = 'brush'">
                <Brush :size="17" />
              </button>
              <button type="button" title="橡皮" :class="{ active: tool === 'eraser' }" @click="tool = 'eraser'">
                <Eraser :size="17" />
              </button>
              <button type="button" title="撤销" :disabled="!strokes.length" @click="undoStroke">
                <Undo2 :size="17" />
              </button>
              <button type="button" title="清空" :disabled="!strokes.length" @click="clearMask">
                <Trash2 :size="17" />
              </button>
            </div>

            <label class="local-edit-field local-edit-size-field">
              <span>画笔大小</span>
              <input v-model.number="brushSize" type="range" min="8" max="160" step="2" />
              <output>{{ brushSize }}px</output>
            </label>

            <label class="local-edit-field">
              <span>提示词</span>
              <textarea v-model.trim="prompt" placeholder="描述选中区域要如何改变"></textarea>
            </label>

            <label class="local-edit-field">
              <span>质量</span>
              <select v-model="quality">
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </select>
            </label>

            <p v-if="errorMessage" class="local-edit-error">{{ errorMessage }}</p>

            <button type="button" class="local-edit-submit" :disabled="!canSubmit" @click="submitLocalEdit">
              <LoaderCircle v-if="busy || preparingMask" :size="16" class="spin" />
              <WandSparkles v-else :size="16" />
              <span>{{ busy || preparingMask ? '提交中' : '提交局部修改' }}</span>
            </button>
          </aside>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Brush, Eraser, ImageOff, LoaderCircle, Trash2, Undo2, WandSparkles, X } from '@lucide/vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  item: { type: Object, default: null },
  busy: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'submit'])

const imageRef = ref(null)
const maskCanvas = ref(null)
const tool = ref('brush')
const brushSize = ref(48)
const prompt = ref('')
const quality = ref('low')
const imageReady = ref(false)
const imageError = ref(false)
const errorMessage = ref('')
const preparingMask = ref(false)
const sourceSize = ref({ width: 0, height: 0 })
const strokes = ref([])
let drawing = false
let activePointerId = null
let currentStroke = null

const imageUrl = computed(() => props.item?.asset?.url || props.item?.asset?.thumbnail_url || '')
const itemTitle = computed(() => props.item?.title || props.item?.asset?.title || '图片素材')
const canSubmit = computed(() => (
  props.open &&
  imageReady.value &&
  !props.busy &&
  !preparingMask.value &&
  Boolean(prompt.value.trim())
))

watch(
  () => props.open,
  async (value) => {
    if (!value) return
    resetDialog()
    await nextTick()
    syncImageElement()
  },
)

watch(imageUrl, async () => {
  if (!props.open) return
  resetCanvasState()
  await nextTick()
  syncImageElement()
})

function resetDialog() {
  tool.value = 'brush'
  brushSize.value = 48
  prompt.value = ''
  quality.value = 'low'
  errorMessage.value = ''
  preparingMask.value = false
  resetCanvasState()
}

function resetCanvasState() {
  drawing = false
  activePointerId = null
  currentStroke = null
  strokes.value = []
  imageReady.value = false
  imageError.value = false
  sourceSize.value = { width: 0, height: 0 }
  clearCanvas()
}

function handleClose() {
  if (props.busy || preparingMask.value) return
  emit('close')
}

function handleImageError() {
  imageError.value = true
  imageReady.value = false
}

function syncImageElement() {
  const image = imageRef.value
  const canvas = maskCanvas.value
  if (!image || !canvas || !image.complete || !image.naturalWidth || !image.naturalHeight) return

  sourceSize.value = {
    width: image.naturalWidth,
    height: image.naturalHeight,
  }
  canvas.width = image.naturalWidth
  canvas.height = image.naturalHeight
  imageReady.value = true
  imageError.value = false
  renderAllStrokes()
}

function canvasContext() {
  const canvas = maskCanvas.value
  return canvas ? canvas.getContext('2d') : null
}

function clearCanvas() {
  const canvas = maskCanvas.value
  const context = canvasContext()
  if (!canvas || !context) return
  context.clearRect(0, 0, canvas.width, canvas.height)
}

function eventToCanvasPoint(event) {
  const canvas = maskCanvas.value
  if (!canvas) return null
  const rect = canvas.getBoundingClientRect()
  if (!rect.width || !rect.height) return null
  const x = ((event.clientX - rect.left) / rect.width) * canvas.width
  const y = ((event.clientY - rect.top) / rect.height) * canvas.height
  return {
    x: Math.max(0, Math.min(canvas.width, x)),
    y: Math.max(0, Math.min(canvas.height, y)),
  }
}

function startStroke(event) {
  if (!imageReady.value || props.busy || preparingMask.value) return
  const point = eventToCanvasPoint(event)
  if (!point) return
  errorMessage.value = ''
  drawing = true
  activePointerId = event.pointerId
  currentStroke = {
    tool: tool.value,
    size: Number(brushSize.value) || 48,
    points: [point],
  }
  maskCanvas.value?.setPointerCapture?.(event.pointerId)
  drawPoint(currentStroke, point)
  event.preventDefault()
}

function continueStroke(event) {
  if (!drawing || event.pointerId !== activePointerId || !currentStroke) return
  const point = eventToCanvasPoint(event)
  if (!point) return
  const previous = currentStroke.points[currentStroke.points.length - 1]
  currentStroke.points.push(point)
  drawSegment(currentStroke, previous, point)
  event.preventDefault()
}

function finishStroke(event) {
  if (!drawing || (event?.pointerId != null && event.pointerId !== activePointerId)) return
  if (currentStroke?.points?.length) {
    strokes.value = [...strokes.value, currentStroke]
  }
  if (activePointerId != null) {
    maskCanvas.value?.releasePointerCapture?.(activePointerId)
  }
  drawing = false
  activePointerId = null
  currentStroke = null
}

function applyStrokeStyle(context, stroke) {
  context.lineCap = 'round'
  context.lineJoin = 'round'
  context.lineWidth = stroke.size
  if (stroke.tool === 'eraser') {
    context.globalCompositeOperation = 'destination-out'
    context.strokeStyle = 'rgba(0, 0, 0, 1)'
    context.fillStyle = 'rgba(0, 0, 0, 1)'
  } else {
    context.globalCompositeOperation = 'source-over'
    context.strokeStyle = 'rgba(60, 110, 232, 0.58)'
    context.fillStyle = 'rgba(60, 110, 232, 0.58)'
  }
}

function drawPoint(stroke, point) {
  const context = canvasContext()
  if (!context) return
  context.save()
  applyStrokeStyle(context, stroke)
  context.beginPath()
  context.arc(point.x, point.y, stroke.size / 2, 0, Math.PI * 2)
  context.fill()
  context.restore()
}

function drawSegment(stroke, from, to) {
  const context = canvasContext()
  if (!context) return
  context.save()
  applyStrokeStyle(context, stroke)
  context.beginPath()
  context.moveTo(from.x, from.y)
  context.lineTo(to.x, to.y)
  context.stroke()
  context.restore()
}

function renderStroke(stroke) {
  if (!stroke.points.length) return
  if (stroke.points.length === 1) {
    drawPoint(stroke, stroke.points[0])
    return
  }
  for (let index = 1; index < stroke.points.length; index += 1) {
    drawSegment(stroke, stroke.points[index - 1], stroke.points[index])
  }
}

function renderAllStrokes() {
  clearCanvas()
  for (const stroke of strokes.value) {
    renderStroke(stroke)
  }
}

function undoStroke() {
  if (!strokes.value.length) return
  strokes.value = strokes.value.slice(0, -1)
  renderAllStrokes()
}

function clearMask() {
  strokes.value = []
  renderAllStrokes()
}

function hasPaintedPixels() {
  const canvas = maskCanvas.value
  const context = canvasContext()
  if (!canvas || !context || !canvas.width || !canvas.height) return false
  const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
  for (let index = 3; index < pixels.length; index += 4) {
    if (pixels[index] > 0) return true
  }
  return false
}

async function createMaskBlob() {
  const canvas = maskCanvas.value
  if (!canvas || !canvas.width || !canvas.height) return null
  if (!hasPaintedPixels()) return null

  const output = document.createElement('canvas')
  output.width = canvas.width
  output.height = canvas.height
  const context = output.getContext('2d')
  context.fillStyle = 'rgba(255, 255, 255, 1)'
  context.fillRect(0, 0, output.width, output.height)

  // 提交给上游的 mask 使用 OpenAI 兼容语义：透明区域表示要修改。
  // 用户在界面上涂抹的是蓝色可见区域，这里统一转换为 alpha=0。
  context.globalCompositeOperation = 'destination-out'
  context.drawImage(canvas, 0, 0)
  context.globalCompositeOperation = 'source-over'

  return new Promise((resolve) => {
    output.toBlob(blob => resolve(blob), 'image/png')
  })
}

async function submitLocalEdit() {
  if (!prompt.value.trim()) {
    errorMessage.value = '请输入提示词'
    return
  }
  if (!imageReady.value) {
    errorMessage.value = '图片尚未载入'
    return
  }

  preparingMask.value = true
  errorMessage.value = ''
  try {
    const maskBlob = await createMaskBlob()
    if (!maskBlob) {
      errorMessage.value = '请先涂抹要修改的区域'
      return
    }
    emit('submit', {
      item: props.item,
      prompt: prompt.value.trim(),
      quality: quality.value,
      maskBlob,
      width: sourceSize.value.width,
      height: sourceSize.value.height,
    })
  } finally {
    preparingMask.value = false
  }
}
</script>

<style scoped>
.local-edit-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 18, 22, 0.62);
}

.local-edit-dialog {
  width: min(1120px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid rgba(23, 23, 23, 0.12);
  border-radius: 8px;
  background: #f8f8f5;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
}

.local-edit-header {
  min-width: 0;
  height: 58px;
  padding: 0 16px 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(23, 23, 23, 0.12);
  background: rgba(255, 255, 255, 0.92);
}

.local-edit-header div {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.local-edit-header strong,
.local-edit-header span,
.local-edit-field span,
.local-edit-field output,
.local-edit-error,
.local-edit-submit,
.local-edit-image-error {
  font-family: var(--font-ui);
}

.local-edit-header strong {
  color: var(--color-ink);
  font-size: 14px;
  font-weight: 900;
}

.local-edit-header span {
  overflow: hidden;
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.local-edit-header button,
.local-edit-tool-row button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-line);
  border-radius: 8px;
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
}

.local-edit-header button {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
}

.local-edit-body {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 292px;
}

.local-edit-stage-shell {
  min-width: 0;
  min-height: 0;
  display: grid;
  place-items: center;
  overflow: auto;
  padding: 18px;
  background:
    linear-gradient(90deg, rgba(23, 23, 23, 0.05) 1px, transparent 1px),
    linear-gradient(180deg, rgba(23, 23, 23, 0.05) 1px, transparent 1px),
    #eeeeea;
  background-size: 28px 28px;
}

.local-edit-stage {
  position: relative;
  display: inline-block;
  max-width: 100%;
  max-height: calc(100vh - 132px);
  overflow: hidden;
  border: 1px solid rgba(23, 23, 23, 0.12);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 14px 34px rgba(23, 23, 23, 0.14);
}

.local-edit-stage img {
  display: block;
  max-width: 100%;
  max-height: calc(100vh - 132px);
  user-select: none;
}

.local-edit-mask-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: crosshair;
}

.local-edit-mask-canvas.disabled {
  cursor: wait;
  pointer-events: none;
}

.local-edit-image-error {
  min-height: 220px;
  min-width: min(420px, 80vw);
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  border: 1px dashed var(--color-line-strong);
  border-radius: 8px;
  color: var(--color-muted);
  font-size: 13px;
  font-weight: 800;
}

.local-edit-controls {
  min-width: 0;
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 14px;
  padding: 16px;
  border-left: 1px solid rgba(23, 23, 23, 0.12);
  background: rgba(255, 255, 255, 0.88);
}

.local-edit-tool-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.local-edit-tool-row button {
  height: 38px;
}

.local-edit-tool-row button.active {
  border-color: rgba(60, 110, 232, 0.48);
  background: rgba(60, 110, 232, 0.12);
  color: var(--color-blue);
}

.local-edit-tool-row button:disabled,
.local-edit-header button:disabled,
.local-edit-submit:disabled {
  opacity: 0.48;
  cursor: default;
}

.local-edit-field {
  min-width: 0;
  display: grid;
  gap: 7px;
}

.local-edit-size-field {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.local-edit-size-field span,
.local-edit-size-field input {
  grid-column: 1 / -1;
}

.local-edit-field span {
  color: var(--color-muted);
  font-size: 11px;
  font-weight: 900;
}

.local-edit-field output {
  color: var(--color-ink);
  font-size: 11px;
  font-weight: 900;
}

.local-edit-field input,
.local-edit-field select,
.local-edit-field textarea {
  min-width: 0;
  border: 1px solid var(--color-line);
  border-radius: 8px;
  background: #fff;
  color: var(--color-ink);
  outline: none;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.local-edit-field input[type='range'] {
  height: 30px;
}

.local-edit-field select {
  height: 36px;
  padding: 0 10px;
}

.local-edit-field textarea {
  min-height: 152px;
  resize: vertical;
  padding: 10px;
  line-height: 1.5;
}

.local-edit-error {
  margin: 0;
  padding: 9px 10px;
  border: 1px solid rgba(200, 77, 60, 0.22);
  border-radius: 8px;
  background: rgba(200, 77, 60, 0.08);
  color: #b43e2e;
  font-size: 12px;
  font-weight: 800;
}

.local-edit-submit {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 8px;
  background: var(--color-ink);
  color: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
}

.spin {
  animation: local-edit-spin 0.9s linear infinite;
}

@keyframes local-edit-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 860px) {
  .local-edit-backdrop {
    padding: 10px;
  }

  .local-edit-dialog {
    width: calc(100vw - 20px);
    max-height: calc(100vh - 20px);
  }

  .local-edit-body {
    grid-template-columns: 1fr;
    overflow: auto;
  }

  .local-edit-stage-shell {
    min-height: 320px;
  }

  .local-edit-controls {
    border-left: 0;
    border-top: 1px solid rgba(23, 23, 23, 0.12);
  }
}
</style>
