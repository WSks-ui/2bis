<template>
  <section class="generate-section">
    <div class="mode-row">
      <button v-for="item in modes" :key="item.value" :class="{ active: mode === item.value }" @click="switchMode(item.value)">
        {{ item.label }}
      </button>
    </div>

    <div v-if="needImage" class="upload-box" @click="triggerUpload">
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="handleFileSelect" />
      <img v-if="preview" :src="preview" alt="参考图" />
      <span>{{ preview ? '更换图片' : '上传图片' }}</span>
    </div>

    <textarea v-model="prompt" class="prompt-input" rows="4" :placeholder="placeholder"></textarea>

    <div class="quality-row">
      <button v-for="item in qualities" :key="item.value" :class="{ active: quality === item.value }" @click="quality = item.value">
        <strong>{{ item.label }}</strong>
        <span>{{ item.cost }} 额度 · {{ item.source }}</span>
      </button>
    </div>

    <div class="action-row">
      <div class="ratio-row">
        <button
          v-for="item in sizes"
          :key="item.value"
          :class="{ active: size === item.value }"
          @click="size = item.value"
        >
          <strong>{{ item.ratio }}</strong>
          <span>{{ item.label }}</span>
        </button>
      </div>
      <button class="btn-generate" :disabled="generating || !canSubmit" @click="submit">
        {{ generating ? '提交中' : mode === 'edit' ? '开始编辑' : '开始生成' }}
      </button>
    </div>

    <div v-if="imageUrl" class="result-area">
      <img :src="imageUrl" alt="生成结果" />
      <button class="btn-download" @click="downloadImage">下载</button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { usePointsStore } from '../stores/points'

const pointsStore = usePointsStore()

const mode = ref('text2img')
const prompt = ref('')
const quality = ref('low')
const size = ref('1024x1024')
const imageFile = ref(null)
const preview = ref('')
const imageUrl = ref('')
const generating = ref(false)
const fileInput = ref(null)

const modes = [
  { label: '文生图', value: 'text2img' },
  { label: '参考图', value: 'ref2img' },
  { label: '编辑', value: 'edit' }
]

const qualities = [
  { label: '低质量', value: 'low', cost: 1, source: '优先体验积分' },
  { label: '中质量', value: 'medium', cost: 2, source: '优先体验积分' },
  { label: '高质量', value: 'high', cost: 3, source: '订阅额度' }
]

const sizes = [
  { ratio: '1:1', label: '方图 1024×1024', value: '1024x1024' },
  { ratio: '16:9', label: '横版 1344×768', value: '1344x768' },
  { ratio: '9:16', label: '竖版 768×1344', value: '768x1344' },
  { ratio: '1:1 HD', label: '高清方图 2048×2048', value: '2048x2048' }
]

const needImage = computed(() => mode.value !== 'text2img')
const canSubmit = computed(() => {
  if (needImage.value) return Boolean(prompt.value.trim() && imageFile.value)
  return Boolean(prompt.value.trim())
})
const placeholder = computed(() => {
  if (mode.value === 'text2img') return '描述你想生成的画面'
  if (mode.value === 'ref2img') return '结合参考图描述新画面'
  return '描述要如何编辑原图'
})

function switchMode(nextMode) {
  mode.value = nextMode
  imageUrl.value = ''
  if (nextMode === 'text2img') {
    imageFile.value = null
    preview.value = ''
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
  imageFile.value = file
  const reader = new FileReader()
  reader.onload = (readerEvent) => {
    preview.value = readerEvent.target.result
  }
  reader.readAsDataURL(file)
}

async function submit() {
  if (!canSubmit.value) return
  generating.value = true
  try {
    let res
    if (mode.value === 'text2img') {
      res = await api.post('/generate', {
        prompt: prompt.value.trim(),
        quality: quality.value,
        size: size.value
      })
    } else {
      const formData = new FormData()
      formData.append('image', imageFile.value)
      formData.append('prompt', prompt.value.trim())
      formData.append('quality', quality.value)
      formData.append('size', size.value)
      res = await api.post('/edits', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }
    imageUrl.value = res.data.image_url || ''
    await pointsStore.fetchBalance()
    ElMessage.success('任务已提交')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    generating.value = false
  }
}

function downloadImage() {
  if (!imageUrl.value) return
  const a = document.createElement('a')
  a.href = imageUrl.value
  a.download = `2bis-${Date.now()}.png`
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>

<style scoped>
.generate-section {
  display: grid;
  gap: 16px;
}

.mode-row,
.quality-row,
.action-row,
.ratio-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.mode-row button,
.quality-row button,
.ratio-row button,
.btn-generate,
.btn-download,
.size-select {
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-md);
  background: rgba(250, 249, 245, 0.04);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-weight: 700;
}

.mode-row button,
.quality-row button,
.ratio-row button,
.btn-generate,
.btn-download {
  cursor: pointer;
}

.mode-row button {
  padding: 9px 16px;
}

.mode-row button.active,
.quality-row button.active,
.ratio-row button.active {
  color: var(--color-orange);
  border-color: rgba(217, 119, 87, 0.34);
  background: rgba(217, 119, 87, 0.1);
}

.upload-box {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 84px;
  padding: 12px;
  border: 1px dashed rgba(106, 155, 204, 0.34);
  border-radius: var(--radius-md);
  color: var(--color-blue);
  cursor: pointer;
  font-family: var(--font-heading);
  font-weight: 700;
}

.upload-box img {
  width: 70px;
  height: 56px;
  border-radius: var(--radius-sm);
  object-fit: cover;
}

.prompt-input {
  width: 100%;
  padding: 16px;
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-md);
  background: rgba(250, 249, 245, 0.04);
  color: var(--color-light);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.7;
  resize: vertical;
}

.quality-row button {
  min-width: 150px;
  padding: 10px 12px;
  display: grid;
  gap: 4px;
  text-align: left;
}

.quality-row span {
  color: var(--color-mid);
  font-size: 12px;
}

.ratio-row {
  flex: 1 1 360px;
}

.ratio-row button {
  min-width: 118px;
  min-height: 54px;
  padding: 8px 11px;
  display: grid;
  gap: 2px;
  text-align: left;
}

.ratio-row span {
  color: var(--color-mid);
  font-size: 11px;
}

.size-select {
  min-height: 42px;
  padding: 0 12px;
}

.btn-generate {
  min-height: 42px;
  padding: 0 22px;
  border-color: transparent;
  background: var(--color-orange);
  color: var(--color-dark);
}

.btn-download {
  padding: 10px 18px;
}

button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.result-area {
  display: grid;
  gap: 12px;
}

.result-area img {
  width: min(100%, 720px);
  border-radius: var(--radius-md);
}
</style>
