import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const usePointsStore = defineStore('points', () => {
  const balance = ref(0)
  const freePoints = ref(0)
  const isMember = ref(false)
  const memberExpireAt = ref(null)

  async function fetchBalance() {
    try {
      const res = await api.get('/points/balance')
      const data = res.data
      balance.value = data.points ?? 0
      freePoints.value = data.free_points ?? 0
      isMember.value = data.is_member || false
      memberExpireAt.value = data.member_expire_at || null
    } catch (e) {
      console.error('Failed to fetch balance', e)
    }
  }

  return {
    balance,
    freePoints,
    isMember,
    memberExpireAt,
    fetchBalance
  }
})
