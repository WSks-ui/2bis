<template>
  <div class="points-display">
    <el-icon :size="18"><Coin /></el-icon>
    <span class="points-value">{{ balance }}</span>
  </div>
</template>

<script setup>
import { Coin } from '@element-plus/icons-vue'

defineProps({
  balance: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.points-display {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #e6a23c;
  font-weight: 500;
}

.points-value {
  color: #e6a23c;
}
</style>
