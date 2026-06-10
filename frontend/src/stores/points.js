import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '../api'

export const usePointsStore = defineStore('points', () => {
  const balance = ref(0)
  const freePoints = ref(0)
  const freePointsExpireAt = ref(null)
  const monthlyQuotaRemaining = ref(0)
  const monthlyQuotaTotal = ref(0)
  const quotaResetAt = ref(null)
  const subscriptionPlan = ref(null)
  const subscriptionPeriod = ref(null)
  const subscriptionExpireAt = ref(null)
  const trialActivated = ref(false)
  const trialExpireAt = ref(null)

  const isMember = ref(false)
  const memberExpireAt = ref(null)

  const hasQuota = computed(() => monthlyQuotaRemaining.value > 0)
  const planLabel = computed(() => {
    const labels = {
      trial: '体验包',
      light: '轻量版',
      creator: '创作版',
      pro: '专业版'
    }
    return labels[subscriptionPlan.value] || ''
  })

  function applyBalance(data) {
    balance.value = data.monthly_quota_remaining ?? data.points ?? 0
    freePoints.value = data.free_points ?? 0
    freePointsExpireAt.value = data.free_points_expire_at || null
    monthlyQuotaRemaining.value = data.monthly_quota_remaining ?? 0
    monthlyQuotaTotal.value = data.monthly_quota_total ?? 0
    quotaResetAt.value = data.monthly_quota_reset_at || null
    subscriptionPlan.value = data.subscription_plan || null
    subscriptionPeriod.value = data.subscription_period || null
    subscriptionExpireAt.value = data.subscription_expire_at || data.member_expire_at || null
    trialActivated.value = data.trial_activated || false
    trialExpireAt.value = data.trial_expire_at || null
    isMember.value = data.is_member || false
    memberExpireAt.value = data.member_expire_at || null
  }

  async function fetchBalance() {
    try {
      const res = await api.get('/points/balance')
      applyBalance(res.data)
    } catch (e) {
      console.error('Failed to fetch balance', e)
    }
  }

  return {
    balance,
    freePoints,
    freePointsExpireAt,
    monthlyQuotaRemaining,
    monthlyQuotaTotal,
    quotaResetAt,
    subscriptionPlan,
    subscriptionPeriod,
    subscriptionExpireAt,
    trialActivated,
    trialExpireAt,
    isMember,
    memberExpireAt,
    hasQuota,
    planLabel,
    applyBalance,
    fetchBalance
  }
})
