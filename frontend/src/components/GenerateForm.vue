<template>
  <section class="generate-section">
    <div class="generate-hero">
      <h1 class="hero-title">{{ heroTitle }}</h1>
      <p class="hero-subtitle">{{ heroSubtitle }}</p>
    </div>

    <div class="generate-card">
      <div class="card-body">
        <div class="mode-toggle">
          <button
            :class="['mode-btn', { active: mode === 'text2img' }]"
            @click="switchMode('text2img')"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
            文生图
          </button>
          <button
            :class="['mode-btn', { active: mode === 'ref2img' }]"
            @click="switchMode('ref2img')"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            参考图生成
          </button>
          <button
            :class="['mode-btn', { active: mode === 'edit' }]"
            @click="switchMode('edit')"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
            编辑原图
          </button>
        </div>

        <div v-if="mode === 'ref2img' || mode === 'edit'" class="form-group">
          <label class="form-label">{{ mode === 'ref2img' ? '参考图片' : '原图' }}</label>
          <div
            class="upload-area"
            :class="{ 'has-image': refPreview }"
            @click="triggerUpload"
            @dragover.prevent
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              class="file-input-hidden"
              @change="handleFileSelect"
            />
            <template v-if="refPreview">
              <img :src="refPreview" alt="参考图预览" class="ref-preview" />
              <div class="upload-overlay">
                <span>点击更换图片</span>
              </div>
            </template>
            <template v-else>
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
              <span class="upload-text">点击或拖拽上传参考图</span>
              <span class="upload-hint">支持 PNG / JPG / WebP</span>
            </template>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">{{ promptLabel }}</label>
          <textarea
            v-model="prompt"
            class="prompt-input"
            :rows="4"
            :placeholder="promptPlaceholder"
          ></textarea>
        </div>

        <div class="form-actions">
          <div class="selectors-row">
            <div class="quality-selector">
              <span class="form-label">画质</span>
              <div class="quality-options">
                <button
                  v-for="q in qualityOptions"
                  :key="q.value"
                  :class="['quality-btn', { active: quality === q.value }]"
                  @click="quality = q.value"
                >
                  <span class="quality-name">{{ q.label }}</span>
                  <span class="quality-cost">{{ displayCost(q) }} 积分</span>
                </button>
              </div>
            </div>

            <div class="size-selector">
              <span class="form-label">尺寸</span>
              <div class="size-aspect-row">
                <div class="aspect-options">
                  <button
                    v-for="a in aspectOptions"
                    :key="a.value"
                    :class="['aspect-btn', { active: aspect === a.value }]"
                    @click="aspect = a.value"
                  >
                    {{ a.label }}
                  </button>
                </div>
                <div class="size-options">
                  <button
                    v-for="s in currentSizeOptions"
                    :key="s.value"
                    :class="['size-btn', { active: size === s.value }]"
                    @click="size = s.value"
                  >
                    {{ s.label }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="generate-btn-wrap">
            <button
              class="btn-generate"
              :disabled="generating || !canSubmit"
              @click="handleGenerate"
            >
              <span v-if="generating" class="spinner"></span>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
              {{ generating ? '处理中…' : btnLabel }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="imageUrl" class="result-area">
        <div class="result-header">
          <h3 class="result-title">结果</h3>
          <button class="btn-download" @click="downloadImage">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            下载
          </button>
        </div>
        <div class="image-wrapper">
          <img :src="imageUrl" alt="结果" class="result-image" />
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showUpsellModal" class="modal-overlay" @click.self="showUpsellModal = false">
        <div class="modal-card">
          <button class="modal-close" @click="showUpsellModal = false">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
          <div class="upsell-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--color-orange)" stroke-width="1.5">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          </div>
          <h3 class="upsell-title">开通会员，每张图消耗更少</h3>
          <div class="upsell-comparison">
            <div class="compare-col">
              <div class="compare-head">非会员</div>
              <div class="compare-item">中档: 3 积分</div>
              <div class="compare-item">高档: 5 积分</div>
            </div>
            <div class="compare-arrow">→</div>
            <div class="compare-col compare-member">
              <div class="compare-head member-head">月卡会员</div>
              <div class="compare-item">中档: 2 积分</div>
              <div class="compare-item">高档: 3 积分</div>
            </div>
          </div>
          <p class="upsell-desc">月卡每月赠送 260 积分，中档/高档分别省 1~2 分</p>
          <div class="upsell-actions">
            <button class="btn-upsell-ignore" @click="showUpsellModal = false">暂不需要</button>
            <router-link to="/recharge" class="btn-upsell-go" @click="showUpsellModal = false">去看看</router-link>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { usePointsStore } from '../stores/points'
import { useUserStore } from '../stores/user'

const pointsStore = usePointsStore()
const userStore = useUserStore()

const mode = ref('text2img')
const prompt = ref('')
const quality = ref('low')
const aspect = ref('1:1')
const size = ref('1024x1024')
const generating = ref(false)
const imageUrl = ref('')
const showUpsellModal = ref(false)
const upsellDismissed = ref(false)
const refImage = ref(null)
const refPreview = ref('')
const fileInput = ref(null)

const isMember = computed(() => userStore.isMember || pointsStore.isMember)

const heroTitle = computed(() => {
  if (mode.value === 'text2img') return '用文字创造画面'
  if (mode.value === 'ref2img') return '参考图 + 文字，创造新画面'
  return '上传原图，AI 按指令修改'
})

const heroSubtitle = computed(() => {
  if (mode.value === 'text2img') return '描述你脑海中的画面，AI 为你呈现'
  if (mode.value === 'ref2img') return '上传参考图片，AI 结合你的描述生成新图'
  return '上传需要修改的原图，描述你想要的改动'
})

const promptLabel = computed(() => {
  if (mode.value === 'text2img') return '描述词 Prompt'
  if (mode.value === 'ref2img') return '生成描述 Prompt'
  return '编辑指令 Prompt'
})

const promptPlaceholder = computed(() => {
  if (mode.value === 'text2img') return '例如：一只在月光下奔跑的独角兽，奇幻风格，高清画质，暖色调光影...'
  if (mode.value === 'ref2img') return '例如：参考这张图的风格，生成一张赛博朋克城市夜景...'
  return '例如：把天空换成日落晚霞，增加一些飞鸟...'
})

const btnLabel = computed(() => {
  if (mode.value === 'text2img') return '开始生成'
  if (mode.value === 'ref2img') return '开始生成'
  return '开始编辑'
})

const needImage = computed(() => mode.value === 'ref2img' || mode.value === 'edit')

const canSubmit = computed(() => {
  if (needImage.value) return prompt.value.trim() && refImage.value
  return prompt.value.trim()
})

const qualityOptions = [
  { label: '低档', value: 'low', cost: 1, memberCost: 1 },
  { label: '中档', value: 'medium', cost: 3, memberCost: 2 },
  { label: '高档', value: 'high', cost: 5, memberCost: 3 }
]

const aspectOptions = [
  { label: '21:9', value: '21:9' },
  { label: '16:9', value: '16:9' },
  { label: '3:2', value: '3:2' },
  { label: '4:3', value: '4:3' },
  { label: '1:1', value: '1:1' },
  { label: '3:4', value: '3:4' },
  { label: '2:3', value: '2:3' },
  { label: '9:16', value: '9:16' },
]

const sizeMap = {
  '21:9': [
    { label: '2688×1152', value: '2688x1152' },
    { label: '3360×1440', value: '3360x1440' },
  ],
  '16:9': [
    { label: '1344×768', value: '1344x768' },
    { label: '2688×1536', value: '2688x1536' },
    { label: '3840×2160', value: '3840x2160' },
  ],
  '3:2': [
    { label: '1536×1024', value: '1536x1024' },
    { label: '2304×1536', value: '2304x1536' },
    { label: '3072×2048', value: '3072x2048' },
  ],
  '4:3': [
    { label: '1152×896', value: '1152x896' },
    { label: '2304×1792', value: '2304x1792' },
  ],
  '1:1': [
    { label: '1024', value: '1024x1024' },
    { label: '2048', value: '2048x2048' },
  ],
  '3:4': [
    { label: '896×1152', value: '896x1152' },
    { label: '1792×2304', value: '1792x2304' },
  ],
  '2:3': [
    { label: '1024×1536', value: '1024x1536' },
    { label: '1536×2304', value: '1536x2304' },
    { label: '2048×3072', value: '2048x3072' },
  ],
  '9:16': [
    { label: '720×1280', value: '720x1280' },
    { label: '1440×2560', value: '1440x2560' },
    { label: '2160×3840', value: '2160x3840' },
  ],
}

const currentSizeOptions = computed(() => sizeMap[aspect.value] || sizeMap['1:1'])

watch(aspect, (newAspect) => {
  const firstSize = sizeMap[newAspect]?.[0]?.value
  if (firstSize) size.value = firstSize
})

function displayCost(opt) {
  if (isMember.value && opt.memberCost < opt.cost) {
    return opt.memberCost
  }
  return opt.cost
}

function switchMode(newMode) {
  mode.value = newMode
  imageUrl.value = ''
  if (newMode === 'text2img') {
    refImage.value = null
    refPreview.value = ''
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (file) setFile(file)
}

function handleDrop(e) {
  const file = e.dataTransfer.files[0]
  if (file) setFile(file)
}

function setFile(file) {
  if (!file.type.match(/image\/(png|jpeg|webp)/)) {
    ElMessage.warning('只支持 PNG / JPG / WebP 格式')
    return
  }
  refImage.value = file
  const reader = new FileReader()
  reader.onload = (e) => { refPreview.value = e.target.result }
  reader.readAsDataURL(file)
}

async function handleGenerate() {
  if (!prompt.value.trim()) {
    ElMessage.warning('请输入描述词')
    return
  }
  if (needImage.value && !refImage.value) {
    ElMessage.warning('请上传图片')
    return
  }

  if (!isMember.value && quality.value !== 'low' && !upsellDismissed.value) {
    showUpsellModal.value = true
    return
  }

  await doGenerate()
}

async function doGenerate() {
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
      formData.append('image', refImage.value)
      formData.append('prompt', prompt.value.trim())
      formData.append('quality', quality.value)
      formData.append('size', size.value)
      res = await api.post('/edits', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }
    imageUrl.value = res.data.image_url
    await pointsStore.fetchBalance()
    ElMessage.success(mode.value === 'edit' ? '图片编辑成功' : '图片生成成功')
  } catch (e) {
    const msg = e.response?.data?.detail || '操作失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    generating.value = false
    upsellDismissed.value = false
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
  max-width: 800px;
  margin: 0 auto;
  padding: 60px 24px 80px;
}

.generate-hero {
  text-align: center;
  margin-bottom: 48px;
}

.hero-title {
  font-size: 48px;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.1;
  margin-bottom: 16px;
  background: linear-gradient(135deg, var(--color-light) 0%, var(--color-orange) 60%, var(--color-blue) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-family: var(--font-body);
  font-size: 17px;
  color: var(--color-mid);
  font-style: italic;
  line-height: 1.6;
}

.generate-card {
  background: rgba(232, 230, 220, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.08);
  border-radius: var(--radius-xl);
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.card-body {
  padding: 36px;
}

.mode-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: 28px;
  padding: 6px;
  background: rgba(250, 249, 245, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.08);
  border-radius: var(--radius-lg);
}

.mode-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.mode-btn:hover {
  color: var(--color-light);
}

.mode-btn.active {
  background: rgba(217, 119, 87, 0.12);
  color: var(--color-orange);
}

.form-group {
  margin-bottom: 28px;
}

.form-label {
  display: block;
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-mid);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
}

.upload-area {
  position: relative;
  width: 100%;
  min-height: 180px;
  border: 2px dashed rgba(232, 230, 220, 0.15);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  cursor: pointer;
  transition: all var(--transition-base);
  overflow: hidden;
  background: rgba(250, 249, 245, 0.02);
  color: var(--color-mid);
}

.upload-area:hover {
  border-color: rgba(106, 155, 204, 0.4);
  background: rgba(250, 249, 245, 0.04);
}

.upload-area.has-image {
  border-style: solid;
  border-color: rgba(106, 155, 204, 0.3);
}

.upload-text {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 500;
}

.upload-hint {
  font-size: 12px;
  opacity: 0.5;
}

.ref-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
  max-height: 300px;
}

.upload-overlay {
  position: absolute;
  inset: 0;
  background: rgba(20, 20, 19, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--transition-base);
  font-family: var(--font-heading);
  font-size: 14px;
  color: var(--color-light);
}

.upload-area.has-image:hover .upload-overlay {
  opacity: 1;
}

.file-input-hidden {
  display: none;
}

.prompt-input {
  width: 100%;
  padding: 16px 20px;
  background: rgba(250, 249, 245, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-md);
  color: var(--color-light);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.7;
  resize: vertical;
  transition: all var(--transition-base);
  outline: none;
}

.prompt-input::placeholder {
  color: var(--color-mid);
  opacity: 0.6;
  font-style: italic;
}

.prompt-input:focus {
  border-color: var(--color-orange);
  box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.12);
  background: rgba(250, 249, 245, 0.06);
}

.form-actions {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.selectors-row {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}

.quality-selector {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quality-options {
  display: flex;
  gap: 8px;
}

.quality-btn {
  padding: 12px 20px;
  background: rgba(250, 249, 245, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-base);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 110px;
}

.quality-btn:hover {
  border-color: rgba(232, 230, 220, 0.25);
  color: var(--color-light);
}

.quality-btn.active {
  background: rgba(217, 119, 87, 0.12);
  border-color: var(--color-orange);
  color: var(--color-orange);
}

.quality-name {
  font-weight: 700;
  font-size: 15px;
}

.quality-cost {
  font-size: 11px;
  opacity: 0.7;
}

.size-selector {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.size-aspect-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.aspect-options {
  display: flex;
  gap: 8px;
}

.size-options {
  display: flex;
  gap: 8px;
  padding-left: 4px;
}

.aspect-btn {
  padding: 8px 14px;
  background: rgba(250, 249, 245, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.aspect-btn:hover {
  border-color: rgba(232, 230, 220, 0.25);
  color: var(--color-light);
}

.aspect-btn.active {
  background: rgba(120, 140, 93, 0.12);
  border-color: var(--color-green);
  color: var(--color-green);
}

.size-btn {
  padding: 12px 18px;
  background: rgba(250, 249, 245, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.size-btn:hover {
  border-color: rgba(232, 230, 220, 0.25);
  color: var(--color-light);
}

.size-btn.active {
  background: rgba(106, 155, 204, 0.12);
  border-color: var(--color-blue);
  color: var(--color-blue);
}

.generate-btn-wrap {
  display: flex;
  align-items: flex-end;
}

.btn-generate {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  background: var(--color-orange);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-dark);
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--transition-base);
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.btn-generate:hover:not(:disabled) {
  background: #c8694a;
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(217, 119, 87, 0.3);
}

.btn-generate:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid transparent;
  border-top-color: var(--color-dark);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.result-area {
  border-top: 1px solid rgba(232, 230, 220, 0.08);
  padding: 32px 36px 36px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.result-title {
  font-size: 18px;
  font-weight: 700;
}

.btn-download {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(106, 155, 204, 0.1);
  border: 1px solid rgba(106, 155, 204, 0.2);
  border-radius: var(--radius-md);
  color: var(--color-blue);
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-base);
}

.btn-download:hover {
  background: rgba(106, 155, 204, 0.18);
  border-color: var(--color-blue);
}

.image-wrapper {
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
}

.result-image {
  width: 100%;
  display: block;
  border-radius: var(--radius-lg);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(20, 20, 19, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  animation: fade-in 0.2s ease;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-card {
  position: relative;
  width: 100%;
  max-width: 440px;
  padding: 40px 36px;
  background: var(--color-dark);
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-xl);
  text-align: center;
  animation: slide-up 0.3s ease;
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--color-mid);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.modal-close:hover {
  color: var(--color-light);
  background: rgba(232, 230, 220, 0.06);
}

.upsell-icon {
  margin-bottom: 20px;
}

.upsell-title {
  font-size: 22px;
  margin-bottom: 24px;
}

.upsell-comparison {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 20px;
}

.compare-col {
  padding: 16px 20px;
  border-radius: var(--radius-md);
  text-align: left;
  flex: 1;
  font-size: 13px;
  color: var(--color-mid);
}

.compare-col:first-child {
  background: rgba(232, 230, 220, 0.03);
  border: 1px solid rgba(232, 230, 220, 0.08);
}

.compare-member {
  background: rgba(217, 119, 87, 0.06);
  border: 1px solid rgba(217, 119, 87, 0.2);
}

.compare-head {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--color-mid);
}

.member-head {
  color: var(--color-orange);
}

.compare-item {
  margin-bottom: 4px;
}

.compare-arrow {
  font-size: 20px;
  color: var(--color-orange);
  font-weight: 700;
}

.upsell-desc {
  font-size: 14px;
  color: var(--color-mid);
  margin-bottom: 24px;
  font-style: italic;
}

.upsell-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-upsell-ignore {
  padding: 10px 24px;
  background: transparent;
  border: 1px solid rgba(232, 230, 220, 0.15);
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
}

.btn-upsell-ignore:hover {
  border-color: rgba(232, 230, 220, 0.3);
  color: var(--color-light);
}

.btn-upsell-go {
  padding: 10px 32px;
  background: var(--color-orange);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-dark);
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
  transition: all var(--transition-base);
}

.btn-upsell-go:hover {
  background: #c8694a;
}

@media (max-width: 640px) {
  .hero-title {
    font-size: 32px;
  }

  .form-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .generate-btn-wrap {
    align-items: stretch;
  }

  .btn-generate {
    justify-content: center;
  }

  .card-body {
    padding: 24px;
  }

  .result-area {
    padding: 24px;
  }

  .upsell-comparison {
    flex-direction: column;
  }

  .compare-arrow {
    transform: rotate(90deg);
  }
}
</style>
