<template>
  <div class="history-page">
    <NavBar />
    <div class="history-content">
      <h2 class="page-title">生成历史</h2>

      <div v-if="loading" class="loading-area">
        <el-skeleton :rows="5" animated />
      </div>

      <div v-else-if="!records.length" class="empty-area">
        <el-empty description="暂无生成记录" />
      </div>

      <el-table v-else :data="records" stripe border class="history-table">
        <el-table-column label="图片" width="120">
          <template #default="{ row }">
            <el-image
              :src="row.image_url"
              fit="cover"
              :preview-src-list="[row.image_url]"
              class="thumbnail"
            />
          </template>
        </el-table-column>
        <el-table-column prop="prompt" label="描述词" min-width="200" show-overflow-tooltip />
        <el-table-column prop="quality" label="质量" width="100">
          <template #default="{ row }">
            <el-tag :type="qualityTagType(row.quality)" size="small">
              {{ qualityLabel(row.quality) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="points_cost" label="消耗积分" width="100" />
        <el-table-column prop="created_at" label="生成时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
import NavBar from '../components/NavBar.vue'

const records = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/history')
    records.value = res.data.records || res.data || []
  } catch (e) {
    console.error('Failed to fetch history', e)
  } finally {
    loading.value = false
  }
})

function qualityLabel(quality) {
  const map = { low: '低质量', medium: '中等', high: '高质量' }
  return map[quality] || quality
}

function qualityTagType(quality) {
  const map = { low: 'info', medium: 'warning', high: 'danger' }
  return map[quality] || 'info'
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}
</script>

<style scoped>
.history-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.history-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 20px;
}

.page-title {
  font-size: 20px;
  color: #303133;
  margin: 0 0 20px 0;
  padding-left: 4px;
  border-left: 4px solid #409eff;
}

.loading-area {
  padding: 40px 0;
}

.empty-area {
  padding: 60px 0;
}

.history-table {
  width: 100%;
}

.thumbnail {
  width: 80px;
  height: 60px;
  border-radius: 4px;
}
</style>
