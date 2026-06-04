<template>
  <div class="generate-form">
    <el-card>
      <template #header>
        <h3 class="form-title">AI 图片生成</h3>
      </template>
      <el-form @submit.prevent="handleGenerate">
        <el-form-item label="描述词 (Prompt)">
          <el-input
            v-model="prompt"
            type="textarea"
            :rows="4"
            placeholder="请输入您想要生成的图片描述，例如：一只在月光下奔跑的独角兽，奇幻风格，高清画质"
          />
        </el-form-item>
        <el-form-item label="图片质量">
          <el-select v-model="quality" placeholder="请选择图片质量">
            <el-option label="低质量 (消耗 1 积分)" value="low" />
            <el-option label="中等质量 (消耗 3 积分)" value="medium" />
            <el-option label="高质量 (消耗 5 积分)" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="generating"
            @click="handleGenerate"
          >
            生成图片
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="imageUrl" class="result-area">
        <el-divider />
        <h4>生成结果</h4>
        <div class="image-wrapper">
          <el-image
            :src="imageUrl"
            fit="contain"
            :preview-src-list="[imageUrl]"
            :initial-index="0"
            class="result-image"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { usePointsStore } from '../stores/points'

const pointsStore = usePointsStore()

const prompt = ref('')
const quality = ref('low')
const generating = ref(false)
const imageUrl = ref('')

async function handleGenerate() {
  if (!prompt.value.trim()) {
    ElMessage.warning('请输入图片描述词')
    return
  }

  generating.value = true
  try {
    const res = await api.post('/generate', {
      prompt: prompt.value.trim(),
      quality: quality.value
    })
    imageUrl.value = res.data.image_url
    await pointsStore.fetchBalance()
    ElMessage.success('图片生成成功')
  } catch (e) {
    const msg = e.response?.data?.detail || '图片生成失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.generate-form {
  max-width: 800px;
  margin: 0 auto;
}

.form-title {
  margin: 0;
  font-size: 18px;
}

.result-area {
  margin-top: 8px;
}

.result-area h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
}

.image-wrapper {
  text-align: center;
}

.result-image {
  max-width: 100%;
  max-height: 500px;
  border-radius: 8px;
  cursor: pointer;
}
</style>
