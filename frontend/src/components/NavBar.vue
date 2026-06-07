<template>
  <header class="navbar">
    <div class="navbar-inner">
      <router-link to="/" class="brand">
        <span class="brand-icon">◇</span>
        <span class="brand-text">2Bis</span>
      </router-link>

      <nav class="nav-links">
        <router-link to="/" class="nav-link" active-class="nav-link--active">首页</router-link>
        <router-link to="/recharge" class="nav-link" active-class="nav-link--active">充值</router-link>
        <router-link to="/history" class="nav-link" active-class="nav-link--active">历史</router-link>
      </nav>

      <div class="navbar-actions">
        <button class="btn-checkin" :class="{ 'btn-checkin-done': !checkinAvailable }" :disabled="!checkinAvailable" @click="doCheckin" :title="checkinTitle">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span class="checkin-text">{{ checkinLabel }}</span>
        </button>

        <PointsDisplay :balance="pointsStore.balance" />
        <PointsDisplay :balance="pointsStore.freePoints" :free="true" />

        <span v-if="userStore.isMember" class="member-badge">
          <span class="member-dot"></span>
          会员
        </span>

        <span class="username-text">{{ userStore.username }}</span>

        <button class="btn-logout" @click="userStore.logout" title="退出登录">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </div>

    <div v-if="checkinResult" class="checkin-toast" :class="{ 'toast-out': toastHiding }">
      <span class="toast-icon">🎁</span>
      <span>签到成功! 第 {{ checkinResult.day_number }} 天 +{{ checkinResult.reward }} 免费积分</span>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import { usePointsStore } from '../stores/points'
import PointsDisplay from './PointsDisplay.vue'
import api from '../api'

const userStore = useUserStore()
const pointsStore = usePointsStore()

const checkinAvailable = ref(false)
const checkinDay = ref(0)
const checkinLoading = ref(false)
const checkinResult = ref(null)
const toastHiding = ref(false)
let toastTimer = null

const checkinLabel = computed(() => {
  if (!checkinAvailable.value && checkinDay.value > 0) return '已签到'
  return '签到'
})

const checkinTitle = computed(() => {
  if (!checkinAvailable.value && checkinDay.value > 0) return `今日已签到 (连续第 ${checkinDay.value} 天)`
  return '每日签到领积分'
})

onMounted(async () => {
  try {
    const res = await api.get('/auth/checkin/status')
    checkinAvailable.value = res.data.checkin_available
    checkinDay.value = res.data.consecutive_days
  } catch (_) {}
})

async function doCheckin() {
  if (!checkinAvailable.value || checkinLoading.value) return
  checkinLoading.value = true
  try {
    const res = await api.post('/auth/checkin')
    checkinAvailable.value = false
    checkinDay.value = res.data.consecutive_days
    pointsStore.freePoints = res.data.free_points
    checkinResult.value = res.data
    toastHiding.value = false
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => {
      toastHiding.value = true
      toastTimer = setTimeout(() => { checkinResult.value = null; toastHiding.value = false }, 400)
    }, 2500)
  } catch (_) {
  } finally {
    checkinLoading.value = false
  }
}
</script>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(20, 20, 19, 0.82);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(232, 230, 220, 0.08);
  animation: navbar-in 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

@keyframes navbar-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.navbar-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--color-light);
}

.brand-icon {
  font-size: 22px;
  color: var(--color-orange);
  transform: rotate(45deg);
  display: inline-block;
  animation: brand-spin 20s linear infinite;
}

@keyframes brand-spin {
  from { transform: rotate(45deg); }
  to { transform: rotate(405deg); }
}

.brand-text {
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: var(--color-light);
}

.nav-links {
  display: flex;
  gap: 4px;
}

.nav-link {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-mid);
  text-decoration: none;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  letter-spacing: -0.01em;
}

.nav-link:hover {
  color: var(--color-light);
  background: rgba(232, 230, 220, 0.06);
}

.nav-link--active {
  color: var(--color-orange);
  background: rgba(217, 119, 87, 0.1);
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-checkin {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid rgba(217, 119, 87, 0.3);
  background: rgba(217, 119, 87, 0.1);
  color: var(--color-orange);
  cursor: pointer;
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.btn-checkin:hover:not(:disabled) {
  background: var(--color-orange);
  color: var(--color-dark);
  border-color: var(--color-orange);
  box-shadow: 0 0 16px rgba(217, 119, 87, 0.3);
}

.btn-checkin:active:not(:disabled) {
  transform: scale(0.95);
}

.btn-checkin-done {
  border-color: rgba(120, 140, 93, 0.2);
  background: rgba(120, 140, 93, 0.06);
  color: var(--color-green);
  cursor: default;
}

.btn-checkin-done:hover {
  background: rgba(120, 140, 93, 0.06);
  color: var(--color-green);
  box-shadow: none;
}

.checkin-text {
  letter-spacing: 0.02em;
}

.checkin-toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  padding: 12px 28px;
  border-radius: 20px;
  background: rgba(28, 28, 26, 0.95);
  border: 1px solid rgba(120, 140, 93, 0.3);
  color: var(--color-green);
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(12px);
  animation: toast-in 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.checkin-toast.toast-out {
  animation: toast-out 0.35s ease forwards;
}

@keyframes toast-in {
  from { opacity: 0; transform: translateX(-50%) translateY(-12px) scale(0.95); }
  to { opacity: 1; transform: translateX(-50%) translateY(0) scale(1); }
}

@keyframes toast-out {
  from { opacity: 1; transform: translateX(-50%) translateY(0) scale(1); }
  to { opacity: 0; transform: translateX(-50%) translateY(-8px) scale(0.95); }
}

.username-text {
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-mid);
}

.member-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-orange);
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(217, 119, 87, 0.1);
  border: 1px solid rgba(217, 119, 87, 0.2);
}

.member-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-orange);
  box-shadow: 0 0 6px var(--color-orange);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.btn-logout {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(232, 230, 220, 0.12);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-mid);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.btn-logout:hover {
  color: var(--color-orange);
  border-color: rgba(217, 119, 87, 0.3);
  background: rgba(217, 119, 87, 0.08);
  transform: rotate(90deg) scale(1.1);
}

.btn-logout:active {
  transform: scale(0.9);
}

@media (max-width: 768px) {
  .navbar-inner {
    padding: 0 16px;
  }

  .nav-links {
    display: none;
  }

  .username-text {
    display: none;
  }
}
</style>
