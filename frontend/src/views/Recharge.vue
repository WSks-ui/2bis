<template>
  <div class="recharge-page">
    <NavBar />
    <div class="recharge-content">
      <h2 class="section-title">积分充值</h2>
      <el-row :gutter="20" class="card-row">
        <el-col :span="8" v-for="pack in pointsPacks" :key="pack.id">
          <el-card class="pack-card" shadow="hover">
            <div class="pack-price">¥{{ pack.price }}</div>
            <div class="pack-points">{{ pack.points }} 积分</div>
            <el-button
              type="primary"
              :loading="pack.loading"
              class="pack-btn"
              @click="buyPack('points', pack)"
            >
              购买
            </el-button>
          </el-card>
        </el-col>
      </el-row>

      <h2 class="section-title">会员开通</h2>
      <el-row :gutter="20" class="card-row">
        <el-col :span="8" v-for="pack in membershipPacks" :key="pack.id">
          <el-card class="pack-card member-card" shadow="hover">
            <div class="pack-name">{{ pack.name }}</div>
            <div class="pack-price">¥{{ pack.price }}</div>
            <div class="pack-points">{{ pack.points }} 积分</div>
            <el-button
              type="warning"
              :loading="pack.loading"
              class="pack-btn"
              @click="buyPack('membership', pack)"
            >
              开通
            </el-button>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-dialog v-model="payDialogVisible" title="确认支付" width="420px">
      <div class="pay-info" v-if="currentOrder">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="订单号">{{ currentOrder.order_no }}</el-descriptions-item>
          <el-descriptions-item label="商品">{{ currentOrder.product_name }}</el-descriptions-item>
          <el-descriptions-item label="金额">¥{{ currentOrder.amount }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="payDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="paying" @click="mockPay">
          模拟支付
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import NavBar from '../components/NavBar.vue'
import { usePointsStore } from '../stores/points'
import { useUserStore } from '../stores/user'

const pointsStore = usePointsStore()
const userStore = useUserStore()

const pointsPacks = reactive([
  { id: 1, name: '50积分', price: 10, points: 50, loading: false },
  { id: 2, name: '140积分', price: 25, points: 140, loading: false },
  { id: 3, name: '300积分', price: 50, points: 300, loading: false }
])

const membershipPacks = reactive([
  { id: 1, name: '月卡', price: 39, points: 260, loading: false },
  { id: 2, name: '季卡', price: 109, points: 720, loading: false },
  { id: 3, name: '年卡', price: 399, points: 2700, loading: false }
])

const payDialogVisible = ref(false)
const paying = ref(false)
const currentOrder = ref(null)

async function buyPack(orderType, pack) {
  pack.loading = true
  try {
    const res = await api.post('/payment/orders', {
      order_type: orderType,
      product_id: pack.id
    })
    currentOrder.value = {
      order_no: res.data.order_no,
      product_name: pack.name,
      amount: pack.price
    }
    payDialogVisible.value = true
  } catch (e) {
    const msg = e.response?.data?.detail || '创建订单失败'
    ElMessage.error(msg)
  } finally {
    pack.loading = false
  }
}

async function mockPay() {
  if (!currentOrder.value) return
  paying.value = true
  try {
    await api.post(`/payment/mock-pay-callback?order_no=${currentOrder.value.order_no}`)
    payDialogVisible.value = false
    ElMessage.success('支付成功')
    await pointsStore.fetchBalance()
    await userStore.fetchUserInfo()
  } catch (e) {
    const msg = e.response?.data?.detail || '支付失败'
    ElMessage.error(msg)
  } finally {
    paying.value = false
  }
}
</script>

<style scoped>
.recharge-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.recharge-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 20px;
}

.section-title {
  font-size: 20px;
  color: #303133;
  margin: 0 0 20px 0;
  padding-left: 4px;
  border-left: 4px solid #409eff;
}

.card-row {
  margin-bottom: 40px;
}

.pack-card {
  text-align: center;
  border-radius: 12px;
  transition: transform 0.2s;
}

.pack-card:hover {
  transform: translateY(-4px);
}

.pack-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.pack-price {
  font-size: 36px;
  font-weight: 700;
  color: #e6a23c;
}

.pack-points {
  font-size: 14px;
  color: #909399;
  margin: 8px 0 20px 0;
}

.pack-btn {
  width: 100%;
}

.member-card {
  border: 2px solid #e6a23c;
}

.pay-info {
  padding: 0;
}
</style>
