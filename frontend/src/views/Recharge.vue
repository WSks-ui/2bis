<template>
  <div class="plans-page paper-page">
    <main class="plans-shell">
      <section v-reveal class="plans-hero">
        <div>
          <p class="eyebrow">Plans & Quota</p>
          <h1>计划与订阅</h1>
          <p>选择适合你的计划，解锁更高质量与专业工作流。专业工作流第一版统一按订阅额度扣费。</p>
          <div class="hero-points" aria-label="订阅优势">
            <span>失败自动退款</span>
            <span>额度实时结算</span>
            <span>专业工作流可用</span>
          </div>
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

      <section v-reveal="100" class="billing-toggle" :class="`period-${period}`">
        <span class="toggle-indicator" aria-hidden="true"></span>
        <button :class="{ active: period === 'monthly' }" @click="period = 'monthly'">按月</button>
        <button :class="{ active: period === 'yearly' }" @click="period = 'yearly'">
          按年 <span>省约 {{ yearlySaving }}%</span>
        </button>
      </section>

      <TransitionGroup name="list" tag="section" class="plan-grid">
        <article v-reveal="120" key="trial" class="plan-card surface-card trial-card">
          <div class="plan-head">
            <h2>{{ trialPack.name || '新手体验包' }}</h2>
            <small>低门槛验证出图质量</small>
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
          v-reveal="160"
          class="plan-card surface-card"
          :class="{ featured: plan.plan_key === 'creator' }"
        >
          <div v-if="plan.plan_key === 'creator'" class="recommend-tag">推荐</div>
          <div class="plan-head">
            <h2>{{ plan.name }}</h2>
            <small>{{ planHint(plan) }}</small>
          </div>
          <div class="plan-price">
            ¥{{ planPrice(plan) }}<span>/{{ period === 'monthly' ? '月' : '年' }}</span>
          </div>
          <p v-if="period === 'yearly'" class="price-note">折合 ¥{{ monthlyEquivalent(plan) }}/月</p>
          <p class="quota-line">{{ plan.monthly_quota }} 额度 / 月</p>
          <ul>
            <li>标准生成（低/中/高）</li>
            <li>专业工作流</li>
            <li>并发任务 {{ concurrencyText(plan) }}</li>
            <li v-if="plan.plan_key === 'creator'">优先生成通道</li>
            <li v-if="plan.plan_key === 'pro'">更高任务容量</li>
          </ul>
          <div class="plan-meter" aria-hidden="true">
            <span :style="{ width: planMeterWidth(plan) }"></span>
          </div>
          <button class="plan-button" :class="{ primary: plan.plan_key === 'creator' }" :disabled="loadingPlanId === plan.id" @click="buyPlan(plan)">
            {{ loadingPlanId === plan.id ? '创建中' : `订阅 ${plan.name}` }}
          </button>
        </article>
      </TransitionGroup>

      <section v-reveal="190" class="commercial-strip surface-card">
        <div>
          <span>商业化账务闭环</span>
          <strong>体验积分与订阅额度分开结算，避免专业工作流成本失控。</strong>
        </div>
        <p>当前版本先按额度扣费，上线后根据真实成本、成功率和复用率继续校准套餐。</p>
      </section>

      <section v-reveal="220" class="workflow-section surface-card">
        <div class="workflow-copy">
          <p class="eyebrow">Workflow Billing</p>
          <h2>专业工作流暂不单独支付</h2>
          <p>第一版只走额度扣费。上线测试后再根据真实成本、成功率和用户复用率调整额度。</p>
        </div>
        <div class="workflow-grid">
          <article v-for="workflow in workflowPresets" :key="workflow.workflow_type" v-reveal="260" class="workflow-card">
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
      <Transition name="modal-fade">
      <div v-if="payDialogVisible" class="modal-overlay" @click.self="payDialogVisible = false">
        <Transition name="modal-pop" appear>
        <div class="modal-card">
          <h3>确认支付</h3>
          <div v-if="currentOrder" class="order-info">
            <div><span>订单号</span><strong>{{ currentOrder.order_no }}</strong></div>
            <div><span>商品</span><strong>{{ currentOrder.product_name }}</strong></div>
            <div><span>金额</span><strong>¥{{ currentOrder.amount }}</strong></div>
          </div>
          <p class="payment-note">支付完成后会自动刷新账户额度；如果上游任务失败，已扣额度会回退。</p>
          <div class="modal-actions">
            <button class="btn-ghost" @click="payDialogVisible = false">取消</button>
            <button class="btn-black btn-pay" :disabled="paying" @click="mockPay">
              {{ paying ? '支付中' : '模拟支付' }}
            </button>
          </div>
        </div>
        </Transition>
      </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from '../services/toast'
import api from '../api'
import { usePointsStore } from '../stores/points'
import { useUserStore } from '../stores/user'
import { fetchPlansConfig, readCachedPlans } from '../services/plansCache'

defineOptions({ name: 'Recharge' })

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

onMounted(() => {
  applyPlansConfig(readCachedPlans())
  pointsStore.refreshBalanceQuietly()
  fetchPlans()
})

async function fetchPlans() {
  try {
    applyPlansConfig(await fetchPlansConfig())
  } catch (_) {
    trialPack.value = { id: 1, name: '新手体验包', price: 5, quota: 30, duration_days: 7 }
    subscriptionPlans.value = fallbackPlans
    workflowPresets.value = fallbackWorkflows
    ElMessage.warning('计划信息加载失败，已显示默认配置')
  }
}

function applyPlansConfig(data) {
  if (!data) return
  trialPack.value = data.trial_pack || {}
  subscriptionPlans.value = data.subscription_plans || fallbackPlans
  workflowPresets.value = data.workflow_presets || fallbackWorkflows
}

function planPrice(plan) {
  return period.value === 'monthly' ? plan.monthly_price : plan.yearly_price
}

function monthlyEquivalent(plan) {
  const yearlyPrice = Number(plan.yearly_price || 0)
  if (!yearlyPrice) return plan.monthly_price || 0
  return Math.round(yearlyPrice / 12)
}

function planHint(plan) {
  const hints = {
    light: '个人轻量创作',
    creator: '稳定内容生产',
    pro: '高频团队与批量任务'
  }
  return hints[plan.plan_key] || '按需扩展创作额度'
}

function planMeterWidth(plan) {
  const maxQuota = Math.max(...subscriptionPlans.value.map((item) => Number(item.monthly_quota || 0)), 1)
  const ratio = Math.min(Math.max(Number(plan.monthly_quota || 0) / maxQuota, 0.18), 1)
  return `${Math.round(ratio * 100)}%`
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

.hero-points {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.hero-points span {
  padding: 7px 10px;
  border: 1px solid rgba(60, 110, 232, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
  box-shadow: 0 8px 20px rgba(23, 23, 23, 0.04);
  transition: transform var(--transition-base), border-color var(--transition-base), background var(--transition-base);
}

.hero-points span:hover {
  border-color: rgba(60, 110, 232, 0.22);
  background: rgba(255, 255, 255, 0.8);
  transform: translateY(-2px);
}

.balance-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.balance-card {
  position: relative;
  overflow: hidden;
  min-height: 138px;
  padding: 20px;
  display: grid;
  align-content: start;
  gap: 8px;
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);
}

.balance-card:hover {
  border-color: rgba(60, 110, 232, 0.2);
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}

.balance-card::before,
.plan-card::before,
.workflow-section::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.62), transparent 34%),
    radial-gradient(circle at 20% 0%, rgba(60, 110, 232, 0.09), transparent 16rem);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.balance-card:hover::before,
.plan-card:hover::before,
.workflow-section:hover::before {
  opacity: 1;
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
  position: relative;
  width: max-content;
  margin: 28px 0 22px;
  padding: 4px;
  display: inline-flex;
  gap: 4px;
  border: 1px solid var(--color-line-strong);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
}

.toggle-indicator {
  position: absolute;
  z-index: 0;
  top: 4px;
  bottom: 4px;
  left: 4px;
  width: calc(50% - 6px);
  border-radius: 999px;
  background: #fff;
  box-shadow: var(--shadow-sm);
  transition: transform 260ms cubic-bezier(0.2, 0.9, 0.24, 1.12);
}

.billing-toggle.period-yearly .toggle-indicator {
  transform: translateX(calc(100% + 8px));
}

.billing-toggle button {
  position: relative;
  z-index: 1;
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
  transition: background var(--transition-base), color var(--transition-base), transform var(--transition-base), box-shadow var(--transition-base);
}

.billing-toggle button.active {
  background: transparent;
  color: var(--color-ink);
  transform: translateY(-1px);
}

.billing-toggle button:hover {
  color: var(--color-ink);
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
  position: relative;
}

.plan-card {
  position: relative;
  overflow: hidden;
  min-height: 340px;
  padding: 26px 22px 20px;
  display: grid;
  grid-template-rows: auto auto auto 1fr auto;
  gap: 16px;
  transform: translateZ(0);
}

.plan-card::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.52), transparent 34%);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.plan-card:hover {
  transform: translateY(-5px) scale(1.01);
}

.plan-card:hover::after {
  opacity: 1;
}

.plan-card.featured {
  border-color: var(--color-ink);
  box-shadow: 0 0 0 1px var(--color-ink), var(--shadow-md);
}

.plan-card.featured:hover {
  box-shadow:
    0 0 0 1px var(--color-ink),
    0 26px 70px rgba(60, 110, 232, 0.14),
    var(--shadow-md);
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
  animation: tag-float 2.8s ease-in-out infinite;
}

.plan-head h2 {
  margin: 0;
  font-size: 18px;
}

.plan-head small {
  margin-top: 6px;
  display: block;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.plan-price {
  color: var(--color-ink);
  font-family: var(--font-heading);
  font-size: 36px;
  font-weight: 850;
  letter-spacing: -0.04em;
  transition: transform var(--transition-base), color var(--transition-base);
}

.plan-card:hover .plan-price {
  color: var(--color-blue);
  transform: translateY(-2px);
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

.price-note {
  width: max-content;
  margin: -8px 0 -4px;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(28, 180, 151, 0.1);
  color: #087e70;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
}

.plan-card li {
  color: var(--color-muted);
  font-size: 13px;
}

.plan-meter {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(226, 229, 223, 0.58);
}

.plan-meter span {
  width: 24%;
  height: 100%;
  display: block;
  border-radius: inherit;
  background: linear-gradient(90deg, #111, rgba(60, 110, 232, 0.72), rgba(28, 180, 151, 0.72));
  transform-origin: left center;
  animation: meter-in 540ms var(--ease-out-soft) both;
}

.plan-button {
  position: relative;
  overflow: hidden;
  min-height: 44px;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.76);
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 850;
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base), background var(--transition-base);
}

.plan-button.primary {
  border-color: var(--color-ink);
  background: linear-gradient(180deg, #252525, #111);
  color: #fff;
}

.plan-button:hover:not(:disabled) {
  border-color: var(--color-ink);
  box-shadow: 0 12px 26px rgba(23, 23, 23, 0.12);
  transform: translateY(-1px);
}

.plan-button:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
}

.plan-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.commercial-strip {
  position: relative;
  overflow: hidden;
  margin-top: 24px;
  padding: 20px 22px;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(246, 244, 238, 0.62)),
    radial-gradient(circle at 8% 0%, rgba(28, 180, 151, 0.12), transparent 18rem);
}

.commercial-strip::after {
  content: '';
  position: absolute;
  inset: auto 22px 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(60, 110, 232, 0.22), transparent);
}

.commercial-strip div {
  display: grid;
  gap: 5px;
}

.commercial-strip span {
  color: var(--color-blue);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.commercial-strip strong {
  color: var(--color-ink);
  font-size: 18px;
}

.commercial-strip p {
  max-width: 430px;
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.7;
}

.workflow-section {
  position: relative;
  overflow: hidden;
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
  position: relative;
  overflow: hidden;
  padding: 17px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.62);
  transition: transform var(--transition-base), border-color var(--transition-base), box-shadow var(--transition-base);
}

.workflow-card:hover {
  border-color: rgba(60, 110, 232, 0.24);
  box-shadow: 0 14px 30px rgba(23, 23, 23, 0.08);
  transform: translateY(-3px);
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
  transition: transform var(--transition-base), background var(--transition-base);
}

.workflow-card:hover .workflow-costs span {
  background: rgba(60, 110, 232, 0.12);
  transform: translateY(-1px);
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
  transform-origin: center;
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

.payment-note {
  margin: -8px 0 20px;
  padding: 12px 14px;
  border: 1px solid rgba(28, 180, 151, 0.14);
  border-radius: var(--radius-md);
  background: rgba(28, 180, 151, 0.07);
  color: #087e70;
  font-size: 13px;
  line-height: 1.7;
}

.btn-ghost,
.btn-pay {
  min-height: 42px;
  padding: 0 18px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-ui);
  font-weight: 850;
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);
}

.btn-ghost {
  border: 1px solid var(--color-line-strong);
  background: transparent;
  color: var(--color-muted);
}

.btn-ghost:hover,
.btn-pay:hover:not(:disabled) {
  box-shadow: 0 10px 22px rgba(23, 23, 23, 0.09);
  transform: translateY(-1px);
}

.btn-ghost:active,
.btn-pay:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
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

@keyframes tag-float {
  0%, 100% {
    transform: translateX(-50%) translateY(0);
  }

  50% {
    transform: translateX(-50%) translateY(-3px);
  }
}

@keyframes meter-in {
  from {
    transform: scaleX(0);
  }

  to {
    transform: scaleX(1);
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

  .toggle-indicator {
    width: calc(50% - 6px);
  }

  .commercial-strip {
    align-items: flex-start;
    flex-direction: column;
  }

  .plan-card {
    min-height: auto;
  }

  .modal-actions {
    align-items: stretch;
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .recommend-tag,
  .plan-meter span {
    animation: none;
  }

  .balance-card:hover,
  .plan-card:hover,
  .workflow-card:hover,
  .hero-points span:hover {
    transform: none;
  }
}
</style>
