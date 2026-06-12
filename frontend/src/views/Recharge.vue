<template>
  <div class="plans-page paper-page">
    <NavBar />

    <main class="plans-shell">
      <section class="plans-hero">
        <div>
          <p class="eyebrow">Plans & Quota</p>
          <h1>计划与订阅</h1>
          <p>选择适合你的计划，解锁更高质量与专业工作流。专业工作流第一版统一按订阅额度扣费。</p>
        </div>
        <div class="balance-cards">
          <article class="surface-card balance-card">
            <span>体验积分</span>
            <strong>{{ pointsStore.freePoints }}</strong>
            <small>用于标准生成的低/中质量试用</small>
          </article>
          <article class="surface-card balance-card highlight">
            <span>订阅额度</span>
            <strong>{{ pointsStore.monthlyQuotaRemaining }}</strong>
            <small>用于高质量生成与专业工作流</small>
          </article>
          <article class="surface-card balance-card rules">
            <span>计费规则说明</span>
            <ul>
              <li>体验积分仅用于标准生成的低/中质量</li>
              <li>订阅额度用于高质量与专业工作流</li>
              <li>失败任务会自动退款</li>
            </ul>
          </article>
        </div>
      </section>

      <section class="billing-toggle">
        <button :class="{ active: period === 'monthly' }" @click="period = 'monthly'">按月</button>
        <button :class="{ active: period === 'yearly' }" @click="period = 'yearly'">
          按年 <span>省约 {{ yearlySaving }}%</span>
        </button>
      </section>

      <section class="plan-grid">
        <article class="plan-card surface-card trial-card">
          <div class="plan-head">
            <h2>{{ trialPack.name || '新手体验包' }}</h2>
          </div>
          <div class="plan-price">
            ¥{{ trialPack.price || 5 }}<span>/{{ trialPack.duration_days || 7 }} 天</span>
          </div>
          <p class="quota-line">{{ trialPack.quota || 30 }} 额度 / 体验期</p>
          <ul>
            <li>适合首次测试生成质量</li>
            <li>支持高质量生成</li>
            <li>不可与有效订阅叠加购买</li>
          </ul>
          <button class="plan-button" :disabled="pointsStore.trialActivated || trialLoading" @click="buyTrial">
            {{ pointsStore.trialActivated ? '已使用' : trialLoading ? '创建中' : '立即体验' }}
          </button>
        </article>

        <article
          v-for="plan in subscriptionPlans"
          :key="plan.id"
          class="plan-card surface-card"
          :class="{ featured: plan.plan_key === 'creator' }"
        >
          <div v-if="plan.plan_key === 'creator'" class="recommend-tag">推荐</div>
          <div class="plan-head">
            <h2>{{ plan.name }}</h2>
          </div>
          <div class="plan-price">
            ¥{{ planPrice(plan) }}<span>/{{ period === 'monthly' ? '月' : '年' }}</span>
          </div>
          <p class="quota-line">{{ plan.monthly_quota }} 额度 / 月</p>
          <ul>
            <li>标准生成（低/中/高）</li>
            <li>专业工作流</li>
            <li>并发任务 {{ concurrencyText(plan) }}</li>
            <li v-if="plan.plan_key === 'creator'">优先生成通道</li>
            <li v-if="plan.plan_key === 'pro'">更高任务容量</li>
          </ul>
          <button class="plan-button" :class="{ primary: plan.plan_key === 'creator' }" :disabled="loadingPlanId === plan.id" @click="buyPlan(plan)">
            {{ loadingPlanId === plan.id ? '创建中' : `订阅 ${plan.name}` }}
          </button>
        </article>
      </section>

      <section class="workflow-section surface-card">
        <div class="workflow-copy">
          <p class="eyebrow">Workflow Billing</p>
          <h2>专业工作流暂不单独支付</h2>
          <p>第一版只走额度扣费。上线测试后再根据真实成本、成功率和用户复用率调整额度。</p>
        </div>
        <div class="workflow-grid">
          <article v-for="workflow in workflowPresets" :key="workflow.workflow_type" class="workflow-card">
            <h3>{{ workflow.name }}</h3>
            <p>{{ workflow.description }}</p>
            <div class="workflow-costs">
              <span>低 {{ workflow.costs?.low ?? 0 }} 额度</span>
              <span>中 {{ workflow.costs?.medium ?? 0 }} 额度</span>
              <span>高 {{ workflow.costs?.high ?? 0 }} 额度</span>
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
            <button class="btn-black btn-pay" :disabled="paying" @click="mockPay">
              {{ paying ? '支付中' : '模拟支付' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
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

const yearlySaving = computed(() => {
  const creator = subscriptionPlans.value.find((plan) => plan.plan_key === 'creator') || subscriptionPlans.value[0]
  if (!creator?.monthly_price || !creator?.yearly_price) return 20
  return Math.max(0, Math.round((1 - creator.yearly_price / (creator.monthly_price * 12)) * 100))
})

onMounted(async () => {
  await pointsStore.refreshBalanceQuietly()
  await fetchPlans()
})

async function fetchPlans() {
  try {
    const res = await api.get('/points/plans')
    trialPack.value = res.data.trial_pack || {}
    subscriptionPlans.value = res.data.subscription_plans || fallbackPlans
    workflowPresets.value = res.data.workflow_presets || fallbackWorkflows
  } catch (_) {
    trialPack.value = { id: 1, name: '新手体验包', price: 5, quota: 30, duration_days: 7 }
    subscriptionPlans.value = fallbackPlans
    workflowPresets.value = fallbackWorkflows
    ElMessage.warning('计划信息加载失败，已显示默认配置')
  }
}

function planPrice(plan) {
  return period.value === 'monthly' ? plan.monthly_price : plan.yearly_price
}

function concurrencyText(plan) {
  if (plan.plan_key === 'pro') return '10 个'
  if (plan.plan_key === 'creator') return '5 个'
  return '2 个'
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
    await userStore.refreshUserInfoQuietly()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '支付失败')
  } finally {
    paying.value = false
  }
}
</script>

<style scoped>
.plans-shell {
  max-width: 1260px;
  margin: 0 auto;
  padding: 42px 28px 100px;
}

.plans-hero {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) 1.45fr;
  gap: 34px;
  align-items: end;
}

.eyebrow {
  margin: 0 0 9px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.plans-hero h1,
.workflow-copy h2 {
  margin: 0;
  font-size: clamp(34px, 5vw, 58px);
  letter-spacing: -0.06em;
}

.plans-hero p,
.workflow-copy p {
  max-width: 520px;
  margin: 12px 0 0;
  color: var(--color-muted);
  font-size: 15px;
}

.balance-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.balance-card {
  min-height: 138px;
  padding: 20px;
  display: grid;
  align-content: start;
  gap: 8px;
}

.balance-card span {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 850;
}

.balance-card strong {
  color: var(--color-ink);
  font-family: var(--font-heading);
  font-size: 34px;
  line-height: 1;
}

.balance-card.highlight strong {
  color: var(--color-blue);
}

.balance-card small,
.balance-card li {
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.65;
}

.balance-card ul,
.plan-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.balance-card li::before,
.plan-card li::before {
  content: '✓';
  margin-right: 8px;
  color: var(--color-green);
  font-family: var(--font-ui);
  font-weight: 900;
}

.billing-toggle {
  width: max-content;
  margin: 28px 0 22px;
  padding: 4px;
  display: inline-flex;
  gap: 4px;
  border: 1px solid var(--color-line-strong);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
}

.billing-toggle button {
  min-width: 76px;
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 850;
}

.billing-toggle button.active {
  background: #fff;
  color: var(--color-ink);
  box-shadow: var(--shadow-sm);
}

.billing-toggle span {
  color: var(--color-blue);
  font-size: 11px;
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  align-items: stretch;
}

.plan-card {
  position: relative;
  min-height: 340px;
  padding: 26px 22px 20px;
  display: grid;
  grid-template-rows: auto auto auto 1fr auto;
  gap: 16px;
}

.plan-card.featured {
  border-color: var(--color-ink);
  box-shadow: 0 0 0 1px var(--color-ink), var(--shadow-md);
}

.recommend-tag {
  position: absolute;
  top: -14px;
  left: 50%;
  padding: 5px 16px;
  border: 1px solid var(--color-ink);
  border-radius: 999px;
  background: #fff;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
  transform: translateX(-50%);
}

.plan-head h2 {
  margin: 0;
  font-size: 18px;
}

.plan-price {
  color: var(--color-ink);
  font-family: var(--font-heading);
  font-size: 36px;
  font-weight: 850;
  letter-spacing: -0.04em;
}

.plan-price span {
  margin-left: 4px;
  color: var(--color-muted);
  font-size: 14px;
  font-weight: 600;
}

.quota-line {
  margin: 0;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 750;
}

.plan-card li {
  color: var(--color-muted);
  font-size: 13px;
}

.plan-button {
  min-height: 44px;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.76);
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 850;
}

.plan-button.primary {
  border-color: var(--color-ink);
  background: linear-gradient(180deg, #252525, #111);
  color: #fff;
}

.plan-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.workflow-section {
  margin-top: 32px;
  padding: 26px;
  display: grid;
  grid-template-columns: 0.85fr 1.4fr;
  gap: 24px;
  align-items: start;
}

.workflow-copy h2 {
  font-size: clamp(26px, 3vw, 38px);
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.workflow-card {
  padding: 17px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.62);
}

.workflow-card h3 {
  margin: 0 0 7px;
  font-size: 16px;
}

.workflow-card p {
  min-height: 42px;
  margin: 0 0 14px;
  color: var(--color-muted);
  font-size: 13px;
}

.workflow-costs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.workflow-costs span {
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(60, 110, 232, 0.08);
  color: var(--color-blue);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(23, 23, 23, 0.38);
  backdrop-filter: blur(10px);
}

.modal-card {
  width: min(430px, 100%);
  padding: 28px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: var(--shadow-lg);
}

.modal-card h3 {
  margin: 0 0 22px;
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
  color: var(--color-muted);
}

.order-info strong {
  color: var(--color-ink);
  text-align: right;
  word-break: break-all;
}

.btn-ghost,
.btn-pay {
  min-height: 42px;
  padding: 0 18px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-ui);
  font-weight: 850;
}

.btn-ghost {
  border: 1px solid var(--color-line-strong);
  background: transparent;
  color: var(--color-muted);
}

@media (max-width: 1100px) {
  .plans-hero,
  .workflow-section {
    grid-template-columns: 1fr;
  }

  .plan-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .plans-shell {
    padding: 28px 14px 96px;
  }

  .balance-cards,
  .plan-grid,
  .workflow-grid {
    grid-template-columns: 1fr;
  }

  .billing-toggle {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .plan-card {
    min-height: auto;
  }

  .modal-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
