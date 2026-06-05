<template>
  <div class="recharge-page">
    <NavBar />

    <div class="page-container">
      <section class="section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="title-accent"></span>
            积分充值
          </h2>
          <p class="section-desc">永久有效，买了就是你的，无过期压力</p>
        </div>

        <div class="card-grid">
          <article v-for="pack in pointsPacks" :key="pack.id" class="pack-card">
            <div class="pack-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="6" x2="12" y2="12" />
                <line x1="12" y1="12" x2="16" y2="14" />
              </svg>
            </div>
            <div class="pack-points-value">{{ pack.points }}<span class="pack-unit"> 积分</span></div>
            <div class="pack-price">¥{{ pack.price }}</div>
            <div class="pack-per-price">≈ ¥{{ pack.perPoint }}/积分</div>
            <div class="pack-tag">{{ pack.tag }}</div>
            <button class="btn-pack" :disabled="pack.loading" @click="buyPack('points', pack)">
              <span v-if="pack.loading" class="spinner-small"></span>
              {{ pack.loading ? '' : '立即购买' }}
            </button>
          </article>
        </div>
      </section>

      <section class="section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="title-accent accent-blue"></span>
            会员开通
          </h2>
          <p class="section-desc">订阅制 · 积分折扣 · 专属权益 · 每月赠送积分</p>
        </div>

        <div class="benefits-table-wrapper">
          <h3 class="subsection-title">会员权益对比</h3>
          <div class="benefits-table">
            <div class="benefit-row benefit-header">
              <div class="benefit-cell label-cell"></div>
              <div class="benefit-cell">非会员</div>
              <div class="benefit-cell">月卡</div>
              <div class="benefit-cell highlight-col">季卡</div>
              <div class="benefit-cell">年卡</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">价格</div>
              <div class="benefit-cell muted">—</div>
              <div class="benefit-cell">¥39/月</div>
              <div class="benefit-cell highlight-col">¥109/季</div>
              <div class="benefit-cell">¥399/年</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">赠送积分</div>
              <div class="benefit-cell muted">—</div>
              <div class="benefit-cell">260</div>
              <div class="benefit-cell highlight-col">720</div>
              <div class="benefit-cell">2700</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">单价</div>
              <div class="benefit-cell muted">0.17-0.20元</div>
              <div class="benefit-cell">0.150元</div>
              <div class="benefit-cell highlight-col">0.151元</div>
              <div class="benefit-cell">0.148元</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">中档消耗</div>
              <div class="benefit-cell">3 积分</div>
              <div class="benefit-cell accented">2 积分</div>
              <div class="benefit-cell highlight-col accented">2 积分</div>
              <div class="benefit-cell accented">2 积分</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">高档(4K)消耗</div>
              <div class="benefit-cell">5 积分</div>
              <div class="benefit-cell accented">3 积分</div>
              <div class="benefit-cell highlight-col accented">3 积分</div>
              <div class="benefit-cell accented">3 积分</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">无水印</div>
              <div class="benefit-cell cross">✕</div>
              <div class="benefit-cell check">✓</div>
              <div class="benefit-cell highlight-col check">✓</div>
              <div class="benefit-cell check">✓</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">优先排队</div>
              <div class="benefit-cell cross">✕</div>
              <div class="benefit-cell check">✓</div>
              <div class="benefit-cell highlight-col check">✓</div>
              <div class="benefit-cell check">✓</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">专属客服</div>
              <div class="benefit-cell cross">✕</div>
              <div class="benefit-cell cross">✕</div>
              <div class="benefit-cell highlight-col check">✓</div>
              <div class="benefit-cell check">✓</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">新功能内测</div>
              <div class="benefit-cell cross">✕</div>
              <div class="benefit-cell cross">✕</div>
              <div class="benefit-cell highlight-col cross">✕</div>
              <div class="benefit-cell check">✓</div>
            </div>
            <div class="benefit-row">
              <div class="benefit-cell label-cell">日均成本</div>
              <div class="benefit-cell muted">—</div>
              <div class="benefit-cell">¥1.30</div>
              <div class="benefit-cell highlight-col">¥1.21</div>
              <div class="benefit-cell">¥1.09</div>
            </div>
          </div>
        </div>

        <div class="card-grid" style="margin-top: 32px;">
          <article
            v-for="pack in membershipPacks"
            :key="pack.id"
            :class="['pack-card', 'member-card', { 'member-featured': pack.id === 2 }]"
          >
            <div v-if="pack.id === 2" class="featured-badge">推荐</div>
            <div class="pack-name">{{ pack.name }}</div>
            <div class="pack-price">¥{{ pack.price }}</div>
            <div class="pack-perk">赠送 {{ pack.points }} 积分</div>
            <div class="pack-per-price">≈ ¥{{ pack.perPoint }}/积分</div>
            <button class="btn-pack btn-member" :disabled="pack.loading" @click="buyPack('membership', pack)">
              <span v-if="pack.loading" class="spinner-small"></span>
              {{ pack.loading ? '' : '立即开通' }}
            </button>
          </article>
        </div>
      </section>

      <section class="section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="title-accent accent-green"></span>
            省钱对比
          </h2>
          <p class="section-desc">以月均生成 100 张 4K 高档图为例</p>
        </div>

        <div class="calc-card">
          <div class="calc-slider">
            <label class="calc-label">我每月大约生成 <strong>{{ calcImages }}</strong> 张 4K 图</label>
            <input
              type="range"
              v-model.number="calcImages"
              min="10"
              max="500"
              step="10"
              class="calc-range"
            />
            <div class="calc-range-labels">
              <span>10张</span>
              <span>100张</span>
              <span>200张</span>
              <span>300张</span>
              <span>500张</span>
            </div>
          </div>

          <div class="calc-result">
            <div class="calc-col">
              <div class="calc-col-head">非会员</div>
              <div class="calc-col-value">¥{{ nonMemberCost.toFixed(1) }}</div>
              <div class="calc-col-desc">{{ calcImages * 5 }} 积分 · 单价 0.17元</div>
            </div>
            <div class="calc-vs">VS</div>
            <div class="calc-col calc-col-member">
              <div class="calc-col-head member-head">月卡会员</div>
              <div class="calc-col-value">¥{{ memberCostCalc.toFixed(1) }}</div>
              <div class="calc-col-desc">{{ calcImages * 3 }} 积分 · 含月费¥39</div>
            </div>
            <div class="calc-col calc-col-save">
              <div class="calc-col-head save-head">为你节省</div>
              <div class="calc-col-value save-value">¥{{ (nonMemberCost - memberCostCalc).toFixed(1) }}</div>
              <div class="calc-col-desc">省 {{ ((nonMemberCost - memberCostCalc) / nonMemberCost * 100).toFixed(0) }}%</div>
            </div>
          </div>
        </div>

        <div class="compare-table" style="margin-top: 40px;">
          <h3 class="subsection-title">透明价格对比表</h3>
          <div class="mini-compare">
            <div class="mini-row mini-head">
              <span>生成 {{ calcImages }} 张 4K 图</span>
              <span>积分消耗</span>
              <span>花费</span>
              <span>节省</span>
            </div>
            <div class="mini-row">
              <span class="label">非会员</span>
              <span>{{ calcImages * 5 }} 分</span>
              <span>¥{{ nonMemberCost.toFixed(1) }}</span>
              <span class="muted">—</span>
            </div>
            <div class="mini-row mini-row-member">
              <span class="label">月卡会员</span>
              <span>{{ calcImages * 3 }} 分</span>
              <span>¥{{ memberCostCalc.toFixed(1) }}</span>
              <span class="save">省 ¥{{ (nonMemberCost - memberCostCalc).toFixed(1) }}</span>
            </div>
            <div class="mini-row mini-row-member">
              <span class="label">年卡(月均)</span>
              <span>{{ calcImages * 3 }} 分</span>
              <span>¥{{ yearlyCostCalc.toFixed(1) }}</span>
              <span class="save">省 ¥{{ (nonMemberCost - yearlyCostCalc).toFixed(1) }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="title-accent accent-blue"></span>
            积分使用规则
          </h2>
        </div>

        <div class="rules-grid">
          <div class="rule-card">
            <div class="rule-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </div>
            <h4 class="rule-title">积分有效期</h4>
            <ul class="rule-list">
              <li>积分包购买：<strong>永久有效</strong></li>
              <li>会员赠送：随会员周期清零</li>
              <li>签到/活动积分：30天有效</li>
            </ul>
          </div>
          <div class="rule-card">
            <div class="rule-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <h4 class="rule-title">消耗规则</h4>
            <ul class="rule-list">
              <li>低档：1分/张（全员统一）</li>
              <li>中档：非会员3分 · 会员<strong>2分</strong></li>
              <li>4K高档：非会员5分 · 会员<strong>3分</strong></li>
            </ul>
          </div>
          <div class="rule-card">
            <div class="rule-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4" />
                <path d="M4 6v12c0 1.1.9 2 2 2h14v-4" />
                <path d="M18 12a2 2 0 0 0-2 2c0 1.1.9 2 2 2h4v-4h-4z" />
              </svg>
            </div>
            <h4 class="rule-title">积分 vs 会员</h4>
            <ul class="rule-list">
              <li>积分包：<strong>永久有效</strong>，适合低频</li>
              <li>会员：月/季/年，适合高频</li>
              <li>可搭配使用：会员积分不够时买积分包补充</li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <Teleport to="body">
      <div v-if="payDialogVisible" class="modal-overlay" @click.self="payDialogVisible = false">
        <div class="modal-card">
          <h3 class="modal-title">确认支付</h3>

          <div v-if="currentOrder" class="order-info">
            <div class="order-row">
              <span class="order-label">订单号</span>
              <span class="order-value">{{ currentOrder.order_no }}</span>
            </div>
            <div class="order-row">
              <span class="order-label">商品</span>
              <span class="order-value">{{ currentOrder.product_name }}</span>
            </div>
            <div class="order-row">
              <span class="order-label">金额</span>
              <span class="order-value order-amount">¥{{ currentOrder.amount }}</span>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn-cancel" @click="payDialogVisible = false">取消</button>
            <button class="btn-pay" :disabled="paying" @click="mockPay">
              <span v-if="paying" class="spinner-small"></span>
              {{ paying ? '支付中…' : '模拟支付' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import NavBar from '../components/NavBar.vue'
import { usePointsStore } from '../stores/points'
import { useUserStore } from '../stores/user'

const pointsStore = usePointsStore()
const userStore = useUserStore()

const calcImages = ref(100)

const pointsPacks = reactive([
  { id: 1, name: '小包', price: 10, points: 50, perPoint: '0.200', tag: '临时补充', loading: false },
  { id: 2, name: '中包', price: 25, points: 140, perPoint: '0.179', tag: '中度使用', loading: false },
  { id: 3, name: '大包', price: 50, points: 300, perPoint: '0.167', tag: '重度囤积', loading: false }
])

const membershipPacks = reactive([
  { id: 1, name: '月卡', price: 39, points: 260, perPoint: '0.150', loading: false },
  { id: 2, name: '季卡', price: 109, points: 720, perPoint: '0.151', loading: false },
  { id: 3, name: '年卡', price: 399, points: 2700, perPoint: '0.148', loading: false }
])

const payDialogVisible = ref(false)
const paying = ref(false)
const currentOrder = ref(null)

const nonMemberCost = computed(() => calcImages.value * 5 * 0.1667)
const memberCostCalc = computed(() => {
  const baseCost = calcImages.value * 3 * 0.15
  const memberFee = 39
  return baseCost + memberFee
})
const yearlyCostCalc = computed(() => {
  const baseCost = calcImages.value * 3 * 0.148
  const memberFee = 399 / 12
  return baseCost + memberFee
})

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
  background: var(--color-dark);
}

.page-container {
  max-width: 1024px;
  margin: 0 auto;
  padding: 48px 24px 80px;
  animation: page-enter 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

@keyframes page-enter {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.section {
  margin-bottom: 72px;
}

.section-header {
  margin-bottom: 32px;
  animation: section-in 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.section:nth-child(1) .section-header { animation-delay: 0.1s; }
.section:nth-child(2) .section-header { animation-delay: 0.2s; }
.section:nth-child(3) .section-header { animation-delay: 0.3s; }
.section:nth-child(4) .section-header { animation-delay: 0.4s; }

@keyframes section-in {
  from { opacity: 0; transform: translateX(-12px); }
  to { opacity: 1; transform: translateX(0); }
}

.section-title {
  font-size: 26px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.title-accent {
  width: 4px;
  height: 26px;
  border-radius: 2px;
  background: var(--color-orange);
  display: inline-block;
}

.title-accent.accent-blue {
  background: var(--color-blue);
}

.title-accent.accent-green {
  background: var(--color-green);
}

.section-desc {
  font-size: 15px;
  color: var(--color-mid);
  margin-top: 10px;
  margin-left: 18px;
  font-style: italic;
}

.subsection-title {
  font-size: 18px;
  margin-bottom: 20px;
  font-weight: 700;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.pack-card {
  position: relative;
  padding: 32px 24px;
  background: rgba(232, 230, 220, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.08);
  border-radius: var(--radius-lg);
  text-align: center;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  animation: card-rise 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.card-grid > *:nth-child(1) { animation-delay: 0.1s; }
.card-grid > *:nth-child(2) { animation-delay: 0.17s; }
.card-grid > *:nth-child(3) { animation-delay: 0.24s; }

@keyframes card-rise {
  from { opacity: 0; transform: translateY(24px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.pack-card:hover {
  transform: translateY(-4px);
  border-color: rgba(232, 230, 220, 0.18);
  box-shadow: var(--shadow-md);
}

.pack-icon {
  color: var(--color-orange);
  opacity: 0.8;
}

.pack-points-value {
  font-family: var(--font-heading);
  font-size: 30px;
  font-weight: 800;
  color: var(--color-light);
  letter-spacing: -0.02em;
}

.pack-unit {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-mid);
}

.pack-price {
  font-family: var(--font-heading);
  font-size: 38px;
  font-weight: 800;
  color: var(--color-orange);
  letter-spacing: -0.03em;
  line-height: 1;
}

.pack-per-price {
  font-size: 12px;
  color: var(--color-mid);
  opacity: 0.7;
}

.pack-tag {
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  background: rgba(120, 140, 93, 0.12);
  color: var(--color-green);
}

.pack-name {
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-light);
}

.pack-perk {
  font-size: 14px;
  color: var(--color-mid);
}

.btn-pack {
  width: 100%;
  padding: 12px;
  background: rgba(217, 119, 87, 0.12);
  border: 1px solid rgba(217, 119, 87, 0.25);
  border-radius: var(--radius-md);
  color: var(--color-orange);
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: auto;
}

.btn-pack:hover:not(:disabled) {
  background: var(--color-orange);
  color: var(--color-dark);
}

.btn-pack:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-member {
  background: rgba(106, 155, 204, 0.12);
  border-color: rgba(106, 155, 204, 0.25);
  color: var(--color-blue);
}

.btn-member:hover:not(:disabled) {
  background: var(--color-blue);
  color: var(--color-dark);
}

.member-card {
  border: 1px solid rgba(106, 155, 204, 0.15);
}

.member-featured {
  border-color: var(--color-blue);
  box-shadow: 0 0 30px rgba(106, 155, 204, 0.08);
}

.featured-badge {
  position: absolute;
  top: -1px;
  right: 20px;
  padding: 4px 14px;
  background: var(--color-blue);
  color: var(--color-dark);
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 700;
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}

.benefits-table-wrapper {
  margin-bottom: 12px;
  overflow-x: auto;
}

.benefits-table {
  display: grid;
  gap: 1px;
  background: rgba(232, 230, 220, 0.06);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid rgba(232, 230, 220, 0.08);
  min-width: 680px;
}

.benefit-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
  gap: 1px;
}

.benefit-row:not(.benefit-header) {
  background: rgba(250, 249, 245, 0.02);
  animation: row-in 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}
.benefit-row:nth-child(2) { animation-delay: 0.05s; }
.benefit-row:nth-child(3) { animation-delay: 0.1s; }
.benefit-row:nth-child(4) { animation-delay: 0.15s; }
.benefit-row:nth-child(5) { animation-delay: 0.2s; }
.benefit-row:nth-child(6) { animation-delay: 0.25s; }
.benefit-row:nth-child(7) { animation-delay: 0.3s; }
.benefit-row:nth-child(8) { animation-delay: 0.35s; }
.benefit-row:nth-child(9) { animation-delay: 0.4s; }
.benefit-row:nth-child(10) { animation-delay: 0.45s; }
.benefit-row:nth-child(11) { animation-delay: 0.5s; }

@keyframes row-in {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}

.benefit-header {
  background: rgba(232, 230, 220, 0.06);
}

.benefit-header .benefit-cell {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 13px;
  color: var(--color-light);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.benefit-cell {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--color-light);
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
}

.label-cell {
  justify-content: flex-start;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-mid);
}

.highlight-col {
  background: rgba(106, 155, 204, 0.06);
}

.accented {
  color: var(--color-green) !important;
  font-weight: 700;
}

.cross {
  color: rgba(250, 249, 245, 0.25);
}

.check {
  color: var(--color-green);
  font-weight: 700;
}

.muted {
  color: var(--color-mid);
  opacity: 0.5;
}

.calc-card {
  padding: 36px;
  background: rgba(232, 230, 220, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.08);
  border-radius: var(--radius-lg);
  animation: card-rise 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.3s both;
}

.calc-slider {
  margin-bottom: 32px;
}

.calc-label {
  display: block;
  font-size: 15px;
  color: var(--color-mid);
  margin-bottom: 20px;
}

.calc-label strong {
  color: var(--color-orange);
  font-family: var(--font-heading);
  font-size: 24px;
}

.calc-range {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(232, 230, 220, 0.12);
  border-radius: 3px;
  outline: none;
}

.calc-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-orange);
  cursor: pointer;
  box-shadow: 0 0 10px rgba(217, 119, 87, 0.4);
}

.calc-range-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: var(--color-mid);
  opacity: 0.6;
}

.calc-result {
  display: flex;
  gap: 16px;
  align-items: stretch;
}

.calc-col {
  flex: 1;
  padding: 24px 16px;
  text-align: center;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}

.calc-col:first-child {
  background: rgba(232, 230, 220, 0.03);
  border: 1px solid rgba(232, 230, 220, 0.08);
}

.calc-col-member {
  background: rgba(217, 119, 87, 0.06);
  border: 1px solid rgba(217, 119, 87, 0.2);
}

.calc-col-save {
  background: rgba(120, 140, 93, 0.08);
  border: 1px solid rgba(120, 140, 93, 0.2);
}

.calc-vs {
  display: flex;
  align-items: center;
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 700;
  color: var(--color-mid);
}

.calc-col-head {
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-mid);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.member-head {
  color: var(--color-orange);
}

.save-head {
  color: var(--color-green);
}

.calc-col-value {
  font-family: var(--font-heading);
  font-size: 32px;
  font-weight: 800;
  color: var(--color-light);
  letter-spacing: -0.03em;
}

.save-value {
  color: var(--color-green);
}

.calc-col-desc {
  font-size: 12px;
  color: var(--color-mid);
}

.mini-compare {
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid rgba(232, 230, 220, 0.08);
}

.mini-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  padding: 14px 20px;
  font-size: 14px;
  color: var(--color-light);
}

.mini-row:not(.mini-head) {
  background: rgba(250, 249, 245, 0.02);
}

.mini-head {
  background: rgba(232, 230, 220, 0.06);
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 12px;
  color: var(--color-mid);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.mini-row-member {
  background: rgba(217, 119, 87, 0.03);
}

.label {
  font-family: var(--font-heading);
  font-weight: 600;
}

.save {
  color: var(--color-green);
  font-weight: 700;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.rule-card {
  padding: 28px 24px;
  background: rgba(232, 230, 220, 0.04);
  border: 1px solid rgba(232, 230, 220, 0.08);
  border-radius: var(--radius-lg);
  transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  animation: card-rise 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.rule-card:hover {
  border-color: rgba(232, 230, 220, 0.16);
  transform: translateY(-2px);
}

.rules-grid > *:nth-child(1) { animation-delay: 0.15s; }
.rules-grid > *:nth-child(2) { animation-delay: 0.22s; }
.rules-grid > *:nth-child(3) { animation-delay: 0.29s; }

.rule-icon {
  color: var(--color-orange);
  margin-bottom: 16px;
}

.rule-title {
  font-size: 16px;
  margin-bottom: 14px;
}

.rule-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rule-list li {
  font-size: 13px;
  color: var(--color-mid);
  padding-left: 16px;
  position: relative;
}

.rule-list li::before {
  content: '·';
  position: absolute;
  left: 2px;
  color: var(--color-orange);
  font-weight: 700;
}

.rule-list li strong {
  color: var(--color-light);
  font-weight: 600;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
  width: 100%;
  max-width: 420px;
  padding: 36px;
  background: var(--color-dark);
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-xl);
  animation: slide-up 0.3s ease;
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-title {
  font-size: 22px;
  margin-bottom: 28px;
}

.order-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

.order-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(232, 230, 220, 0.04);
  border-radius: var(--radius-md);
}

.order-label {
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-mid);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.order-value {
  font-size: 14px;
  color: var(--color-light);
}

.order-amount {
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 800;
  color: var(--color-orange);
}

.modal-actions {
  display: flex;
  gap: 12px;
}

.btn-cancel {
  flex: 1;
  padding: 12px;
  background: transparent;
  border: 1px solid rgba(232, 230, 220, 0.15);
  border-radius: var(--radius-md);
  color: var(--color-mid);
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
}

.btn-cancel:hover {
  border-color: rgba(232, 230, 220, 0.3);
  color: var(--color-light);
}

.btn-pay {
  flex: 2;
  padding: 12px;
  background: var(--color-orange);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-dark);
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-pay:hover:not(:disabled) {
  background: #c8694a;
}

.btn-pay:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .card-grid {
    grid-template-columns: 1fr;
  }

  .calc-result {
    flex-direction: column;
  }

  .calc-vs {
    justify-content: center;
  }

  .rules-grid {
    grid-template-columns: 1fr;
  }

  .section-title {
    font-size: 22px;
  }
}
</style>
