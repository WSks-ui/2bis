<template>
  <div class="plans-page">
    <NavBar />

    <main class="page-container">
      <section class="plans-header">
        <div>
          <h1>选择创作计划</h1>
          <p>体验积分用于低/中质量试用，订阅额度用于完整创作能力。</p>
        </div>
        <div class="balance-strip">
          <div>
            <span class="balance-label">体验积分</span>
            <strong>{{ pointsStore.freePoints }}</strong>
          </div>
          <div>
            <span class="balance-label">订阅额度</span>
            <strong>{{ pointsStore.monthlyQuotaRemaining }}</strong>
          </div>
        </div>
      </section>

      <section class="trial-band">
        <div class="trial-copy">
          <span class="eyebrow">新手体验包</span>
          <h2>{{ trialPack.name || 'Trial Pack' }}</h2>
          <p>7 天内使用 {{ trialPack.quota || 30 }} 订阅额度，支持高质量生成。</p>
        </div>
        <div class="trial-action">
          <div class="trial-price">¥{{ trialPack.price || 5 }}</div>
          <button class="btn-primary" :disabled="pointsStore.trialActivated || trialLoading" @click="buyTrial">
            {{ pointsStore.trialActivated ? '已使用' : trialLoading ? '创建中' : '立即体验' }}
          </button>
        </div>
      </section>

      <section class="subscription-section">
        <div class="section-head">
          <h2>订阅计划</h2>
          <div class="period-toggle">
            <button :class="{ active: period === 'monthly' }" @click="period = 'monthly'">月付</button>
            <button :class="{ active: period === 'yearly' }" @click="period = 'yearly'">年付</button>
          </div>
        </div>

        <div class="plan-grid">
          <article v-for="plan in subscriptionPlans" :key="plan.id" class="plan-card">
            <div class="plan-top">
              <h3>{{ plan.name }}</h3>
              <span v-if="plan.plan_key === 'creator'" class="recommend-tag">推荐</span>
            </div>
            <div class="plan-price">
              ¥{{ planPrice(plan) }}
              <span>/{{ period === 'monthly' ? '月' : '年' }}</span>
            </div>
            <div class="quota-line">{{ plan.monthly_quota }} 额度 / 月</div>
            <ul class="plan-rules">
              <li>低质量：1 额度</li>
              <li>中质量：2 额度</li>
              <li>高质量：3 额度</li>
            </ul>
            <button class="btn-secondary" :disabled="loadingPlanId === plan.id" @click="buyPlan(plan)">
              {{ loadingPlanId === plan.id ? '创建中' : '订阅' }}
            </button>
          </article>
        </div>
      </section>

      <section class="rules-section">
        <div>
          <h2>扣费规则</h2>
          <p>低/中质量优先使用体验积分；体验积分不足以完整支付时，改用订阅额度。高质量始终只使用订阅额度。</p>
        </div>
        <div class="rule-table">
          <span>低质量</span><strong>1</strong>
          <span>中质量</span><strong>2</strong>
          <span>高质量</span><strong>3</strong>
        </div>
      </section>

      <section class="workflow-section">
        <div class="section-head">
          <h2>工作流计费</h2>
          <p>专业工作流第一版不单独收费，直接按订阅额度扣费。</p>
        </div>
        <div class="workflow-grid">
          <article v-for="workflow in workflowPresets" :key="workflow.workflow_type" class="workflow-card">
            <h3>{{ workflow.name }}</h3>
            <p>{{ workflow.description }}</p>
            <div class="workflow-costs">
              <span>低 {{ workflow.costs?.low ?? 0 }}</span>
              <span>中 {{ workflow.costs?.medium ?? 0 }}</span>
              <span>高 {{ workflow.costs?.high ?? 0 }}</span>
            </div>
          </article>
        </div>
      </section>
    </main>

    <Teleport to="body">
      <div v-if="payDialogVisible" class="modal-overlay" @click.self="payDialogVisible = false">
        <div class="modal-card">
          <h3>确认支付</h3>
          <div v-if="currentOrder" class="order-info">
            <div><span>订单号</span><strong>{{ currentOrder.order_no }}</strong></div>
            <div><span>商品</span><strong>{{ currentOrder.product_name }}</strong></div>
            <div><span>金额</span><strong>¥{{ currentOrder.amount }}</strong></div>
          </div>
          <div class="modal-actions">
            <button class="btn-ghost" @click="payDialogVisible = false">取消</button>
            <button class="btn-primary" :disabled="paying" @click="mockPay">
              {{ paying ? '支付中' : '模拟支付' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import NavBar from '../components/NavBar.vue'
import { usePointsStore } from '../stores/points'
import { useUserStore } from '../stores/user'

const pointsStore = usePointsStore()
const userStore = useUserStore()

const period = ref('monthly')
const trialPack = ref({})
const subscriptionPlans = ref([])
const workflowPresets = ref([])
const trialLoading = ref(false)
const loadingPlanId = ref(null)
const payDialogVisible = ref(false)
const paying = ref(false)
const currentOrder = ref(null)

const fallbackPlans = [
  { id: 1, name: 'Light', plan_key: 'light', monthly_price: 29, yearly_price: 268, monthly_quota: 100 },
  { id: 2, name: 'Creator', plan_key: 'creator', monthly_price: 69, yearly_price: 628, monthly_quota: 350 },
  { id: 3, name: 'Pro', plan_key: 'pro', monthly_price: 149, yearly_price: 1368, monthly_quota: 800 }
]

const fallbackWorkflows = [
  {
    workflow_type: 'standard',
    name: '标准生成',
    description: '低/中质量优先使用体验积分。',
    costs: { low: 1, medium: 2, high: 3 }
  },
  {
    workflow_type: 'professional',
    name: '专业工作流',
    description: '统一消耗订阅额度，不做单独支付。',
    costs: { low: 1, medium: 2, high: 3 }
  }
]

onMounted(async () => {
  await pointsStore.fetchBalance()
  await fetchPlans()
})

async function fetchPlans() {
  try {
    const res = await api.get('/points/plans')
    trialPack.value = res.data.trial_pack || {}
    subscriptionPlans.value = res.data.subscription_plans || fallbackPlans
    workflowPresets.value = res.data.workflow_presets || fallbackWorkflows
  } catch (_) {
    trialPack.value = { id: 1, name: 'Trial Pack', price: 5, quota: 30, duration_days: 7 }
    subscriptionPlans.value = fallbackPlans
    workflowPresets.value = fallbackWorkflows
  }
}

function planPrice(plan) {
  return period.value === 'monthly' ? plan.monthly_price : plan.yearly_price
}

async function buyTrial() {
  trialLoading.value = true
  try {
    const pack = trialPack.value
    const res = await api.post('/payment/orders', {
      order_type: 'trial',
      product_id: pack.id || 1
    })
    openPayment(res.data, pack.name || '新手体验包')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建订单失败')
  } finally {
    trialLoading.value = false
  }
}

async function buyPlan(plan) {
  loadingPlanId.value = plan.id
  try {
    const res = await api.post('/payment/orders', {
      order_type: 'subscription',
      product_id: plan.id,
      plan_period: period.value
    })
    openPayment(res.data, `${plan.name} ${period.value === 'monthly' ? '月付' : '年付'}`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建订单失败')
  } finally {
    loadingPlanId.value = null
  }
}

function openPayment(order, productName) {
  currentOrder.value = {
    order_no: order.order_no,
    product_name: productName,
    amount: order.amount
  }
  payDialogVisible.value = true
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
    ElMessage.error(e.response?.data?.detail || '支付失败')
  } finally {
    paying.value = false
  }
}
</script>

<style scoped>
.plans-page {
  min-height: 100vh;
  background: var(--color-dark);
}

.page-container {
  max-width: 1120px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}

.plans-header,
.trial-band,
.rules-section {
  display: flex;
  justify-content: space-between;
  gap: 28px;
  align-items: center;
  margin-bottom: 44px;
}

.workflow-section {
  margin-top: 34px;
}

.workflow-section .section-head {
  align-items: flex-end;
}

.workflow-section .section-head p {
  margin: 0;
  color: var(--color-mid);
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.workflow-card {
  padding: 20px;
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-lg);
  background: rgba(232, 230, 220, 0.04);
}

.workflow-card h3 {
  margin: 0 0 8px;
  color: var(--color-light);
}

.workflow-card p {
  min-height: 46px;
  margin: 0 0 14px;
  color: var(--color-mid);
  line-height: 1.6;
}

.workflow-costs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.workflow-costs span {
  padding: 5px 9px;
  border-radius: var(--radius-sm);
  background: rgba(106, 155, 204, 0.12);
  color: var(--color-blue);
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 700;
}

.plans-header h1,
.trial-copy h2,
.section-head h2,
.rules-section h2 {
  margin: 0;
  font-family: var(--font-heading);
  color: var(--color-light);
}

.plans-header h1 {
  font-size: 38px;
}

.plans-header p,
.trial-copy p,
.rules-section p {
  color: var(--color-mid);
  line-height: 1.7;
  margin: 10px 0 0;
}

.balance-strip {
  display: flex;
  gap: 12px;
}

.balance-strip > div {
  min-width: 124px;
  padding: 14px 16px;
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-md);
  background: rgba(232, 230, 220, 0.04);
}

.balance-label,
.eyebrow {
  display: block;
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}

.balance-strip strong {
  color: var(--color-light);
  font-size: 24px;
}

.trial-band {
  padding: 28px;
  border: 1px solid rgba(217, 119, 87, 0.24);
  border-radius: var(--radius-lg);
  background: rgba(217, 119, 87, 0.07);
}

.trial-action {
  display: flex;
  align-items: center;
  gap: 18px;
}

.trial-price,
.plan-price {
  font-family: var(--font-heading);
  color: var(--color-orange);
  font-size: 34px;
  font-weight: 800;
}

.plan-price span {
  font-size: 14px;
  color: var(--color-mid);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
}

.period-toggle {
  display: flex;
  gap: 6px;
  padding: 4px;
  border-radius: var(--radius-md);
  background: rgba(232, 230, 220, 0.05);
}

.period-toggle button {
  padding: 8px 18px;
  border: none;
  border-radius: calc(var(--radius-md) - 2px);
  background: transparent;
  color: var(--color-mid);
  cursor: pointer;
  font-family: var(--font-heading);
  font-weight: 700;
}

.period-toggle button.active {
  background: rgba(106, 155, 204, 0.18);
  color: var(--color-blue);
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.plan-card {
  padding: 24px;
  border: 1px solid rgba(232, 230, 220, 0.1);
  border-radius: var(--radius-lg);
  background: rgba(232, 230, 220, 0.04);
}

.plan-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.plan-top h3 {
  margin: 0;
  color: var(--color-light);
}

.recommend-tag {
  padding: 4px 8px;
  border-radius: 14px;
  background: rgba(120, 140, 93, 0.16);
  color: var(--color-green);
  font-size: 12px;
  font-weight: 700;
}

.quota-line {
  margin: 14px 0;
  color: var(--color-light);
  font-family: var(--font-heading);
  font-weight: 700;
}

.plan-rules {
  list-style: none;
  padding: 0;
  margin: 0 0 22px;
  display: grid;
  gap: 8px;
  color: var(--color-mid);
  font-size: 14px;
}

.btn-primary,
.btn-secondary,
.btn-ghost {
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 11px 18px;
  font-family: var(--font-heading);
  font-weight: 800;
  cursor: pointer;
}

.btn-primary {
  background: var(--color-orange);
  color: var(--color-dark);
}

.btn-secondary {
  width: 100%;
  background: rgba(106, 155, 204, 0.14);
  border-color: rgba(106, 155, 204, 0.26);
  color: var(--color-blue);
}

.btn-ghost {
  background: transparent;
  border-color: rgba(232, 230, 220, 0.14);
  color: var(--color-mid);
}

button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.rules-section {
  margin-top: 48px;
  padding-top: 30px;
  border-top: 1px solid rgba(232, 230, 220, 0.08);
}

.rule-table {
  min-width: 260px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px 26px;
  color: var(--color-mid);
}

.rule-table strong {
  color: var(--color-light);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(20, 20, 19, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal-card {
  width: min(420px, 100%);
  padding: 30px;
  border-radius: var(--radius-lg);
  background: var(--color-dark);
  border: 1px solid rgba(232, 230, 220, 0.12);
}

.modal-card h3 {
  margin: 0 0 22px;
  color: var(--color-light);
}

.order-info {
  display: grid;
  gap: 12px;
  margin-bottom: 24px;
}

.order-info div,
.modal-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.order-info span {
  color: var(--color-mid);
}

.order-info strong {
  color: var(--color-light);
  text-align: right;
  word-break: break-all;
}

@media (max-width: 820px) {
  .plans-header,
  .trial-band,
  .rules-section {
    align-items: stretch;
    flex-direction: column;
  }

  .balance-strip,
  .trial-action {
    justify-content: space-between;
  }

  .plan-grid {
    grid-template-columns: 1fr;
  }

  .workflow-grid {
    grid-template-columns: 1fr;
  }

  .section-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
  }
}
</style>
