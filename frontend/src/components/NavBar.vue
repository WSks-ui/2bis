<template>
  <header class="navbar">
    <div class="navbar-inner">
      <router-link to="/" class="brand">
        <span class="brand-icon">◆</span>
        <span class="brand-text">2Bis</span>
      </router-link>

      <nav class="nav-links">
        <router-link to="/" class="nav-link" active-class="nav-link--active">首页</router-link>
        <router-link to="/plans" class="nav-link" active-class="nav-link--active">计划</router-link>
        <router-link to="/history" class="nav-link" active-class="nav-link--active">历史</router-link>
      </nav>

      <div class="navbar-actions">
        <button class="btn-checkin" :class="{ 'btn-checkin-done': !checkinAvailable }" :disabled="!checkinAvailable" @click="doCheckin">
          {{ checkinLabel }}
        </button>

        <PointsDisplay :balance="pointsStore.freePoints" label="体验积分" variant="experience" />
        <PointsDisplay :balance="pointsStore.monthlyQuotaRemaining" label="订阅额度" variant="quota" />

        <span v-if="pointsStore.planLabel" class="plan-badge">{{ pointsStore.planLabel }}</span>
        <span class="username-text">{{ userStore.username }}</span>

        <button class="btn-logout" @click="userStore.logout" title="退出登录">
          ×
        </button>
      </div>
    </div>

    <div v-if="checkinResult" class="checkin-toast" :class="{ 'toast-out': toastHiding }">
      签到成功，第 {{ checkinResult.day_number }} 天，+{{ checkinResult.reward }} 体验积分
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
    checkinResult.value = res.data
    await pointsStore.fetchBalance()
    toastHiding.value = false
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => {
      toastHiding.value = true
      toastTimer = setTimeout(() => {
        checkinResult.value = null
        toastHiding.value = false
      }, 400)
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
  background: rgba(20, 20, 19, 0.86);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(232, 230, 220, 0.08);
}

.navbar-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--color-light);
}

.brand-icon {
  color: var(--color-orange);
}

.brand-text {
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 800;
}

.nav-links,
.navbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-link {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-mid);
  text-decoration: none;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
}

.nav-link:hover,
.nav-link--active {
  color: var(--color-orange);
  background: rgba(217, 119, 87, 0.1);
}

.btn-checkin,
.btn-logout {
  border: 1px solid rgba(217, 119, 87, 0.28);
  background: rgba(217, 119, 87, 0.1);
  color: var(--color-orange);
  border-radius: 20px;
  cursor: pointer;
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 700;
}

.btn-checkin {
  padding: 7px 14px;
}

.btn-checkin:disabled {
  color: var(--color-green);
  border-color: rgba(120, 140, 93, 0.22);
  background: rgba(120, 140, 93, 0.08);
  cursor: default;
}

.btn-logout {
  width: 32px;
  height: 32px;
  font-size: 20px;
  line-height: 1;
}

.plan-badge {
  padding: 5px 10px;
  border-radius: 20px;
  border: 1px solid rgba(232, 230, 220, 0.12);
  color: var(--color-light);
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 700;
}

.username-text {
  font-family: var(--font-heading);
  font-size: 13px;
  color: var(--color-mid);
}

.checkin-toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  padding: 12px 24px;
  border-radius: 20px;
  background: rgba(28, 28, 26, 0.96);
  border: 1px solid rgba(120, 140, 93, 0.3);
  color: var(--color-green);
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 700;
}

@media (max-width: 840px) {
  .navbar-inner {
    padding: 10px 16px;
    flex-wrap: wrap;
  }

  .nav-links {
    order: 3;
    width: 100%;
  }

  .username-text,
  .plan-badge {
    display: none;
  }
}
</style>
