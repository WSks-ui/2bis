<template>
  <header class="navbar">
    <div class="navbar-inner">
      <router-link to="/" class="brand" aria-label="2Bis 创作台">
        <span class="brand-word">2Bis</span>
        <span class="brand-subtitle">AI Image Studio</span>
      </router-link>

      <nav class="nav-links" aria-label="主导航">
        <router-link to="/" class="nav-link" active-class="nav-link--active">创作台</router-link>
        <router-link to="/history" class="nav-link" active-class="nav-link--active">历史记录</router-link>
        <router-link to="/plans" class="nav-link" active-class="nav-link--active">计划订阅</router-link>
      </nav>

      <div class="navbar-actions">
        <button
          class="btn-checkin"
          :class="{ 'btn-checkin-done': !checkinAvailable }"
          :disabled="!checkinAvailable"
          @click="doCheckin"
        >
          {{ checkinLabel }}
        </button>

        <div class="balance-pair">
          <PointsDisplay :balance="pointsStore.freePoints" label="体验积分" variant="experience" />
          <PointsDisplay :balance="pointsStore.monthlyQuotaRemaining" label="订阅额度" variant="quota" />
        </div>

        <span v-if="pointsStore.planLabel" class="plan-badge">{{ pointsStore.planLabel }}</span>

        <div class="user-menu-wrap">
          <button class="user-menu" title="账户菜单" @click.stop="toggleUserMenu">
            <span class="avatar">{{ avatarText }}</span>
            <span class="username-text">{{ userStore.username || 'User' }}</span>
            <span class="chevron">⌄</span>
          </button>

          <div v-if="userMenuOpen" class="user-popover" @click.stop>
            <div class="user-popover-head">
              <strong>{{ userStore.username || '未命名用户' }}</strong>
              <span>{{ pointsStore.planLabel || '未订阅' }}</span>
            </div>
            <router-link to="/plans" @click="userMenuOpen = false">管理订阅</router-link>
            <router-link to="/history" @click="userMenuOpen = false">查看历史</router-link>
            <button type="button" class="logout-action" @click="logout">退出登录</button>
          </div>
        </div>
      </div>
    </div>

    <nav class="mobile-tabs" aria-label="移动导航">
      <router-link to="/" class="mobile-tab" active-class="mobile-tab--active">创作</router-link>
      <router-link to="/history" class="mobile-tab" active-class="mobile-tab--active">历史</router-link>
      <router-link to="/plans" class="mobile-tab" active-class="mobile-tab--active">订阅</router-link>
      <button class="mobile-tab mobile-tab-button" :disabled="!checkinAvailable" @click="doCheckin">
        {{ checkinAvailable ? '签到' : '已签' }}
      </button>
    </nav>

    <div v-if="checkinResult" class="checkin-toast" :class="{ 'toast-out': toastHiding }">
      签到成功，第 {{ checkinResult.day_number }} 天，+{{ checkinResult.reward }} 体验积分
    </div>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
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
const userMenuOpen = ref(false)
let toastTimer = null

const checkinLabel = computed(() => {
  if (!checkinAvailable.value && checkinDay.value > 0) return '已签到'
  return '签到'
})

const avatarText = computed(() => {
  const name = userStore.username || '2B'
  return name.slice(0, 1).toUpperCase()
})

onMounted(async () => {
  window.addEventListener('click', closeUserMenu)
  await userStore.refreshUserInfoQuietly()
  try {
    const res = await api.get('/auth/checkin/status')
    checkinAvailable.value = res.data.checkin_available
    checkinDay.value = res.data.consecutive_days
  } catch (_) {}
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeUserMenu)
})

async function doCheckin() {
  if (!checkinAvailable.value || checkinLoading.value) return
  checkinLoading.value = true
  try {
    const res = await api.post('/auth/checkin')
    checkinAvailable.value = false
    checkinDay.value = res.data.consecutive_days
    checkinResult.value = res.data
    await pointsStore.refreshBalanceQuietly()
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
    ElMessage.error('签到失败，请稍后重试')
  } finally {
    checkinLoading.value = false
  }
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value
}

function closeUserMenu() {
  userMenuOpen.value = false
}

function logout() {
  userMenuOpen.value = false
  userStore.logout()
}
</script>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid rgba(207, 212, 203, 0.82);
  background: rgba(251, 251, 248, 0.86);
  backdrop-filter: blur(22px);
}

.navbar-inner {
  max-width: 1480px;
  min-height: 68px;
  margin: 0 auto;
  padding: 0 32px;
  display: grid;
  grid-template-columns: 250px 1fr auto;
  align-items: center;
  gap: 24px;
}

.brand {
  display: inline-flex;
  align-items: baseline;
  gap: 14px;
  width: max-content;
  color: var(--color-ink);
  text-decoration: none;
}

.brand-word {
  font-family: var(--font-heading);
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.08em;
  font-style: italic;
}

.brand-subtitle {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.nav-links {
  display: flex;
  justify-content: center;
  align-self: stretch;
  gap: 34px;
}

.nav-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  transition: color var(--transition-base);
}

.nav-link::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 3px;
  border-radius: 999px;
  background: var(--color-ink);
  transform: scaleX(0);
  transform-origin: center;
  transition: transform var(--transition-base);
}

.nav-link:hover,
.nav-link--active {
  color: var(--color-ink);
}

.nav-link--active::after {
  transform: scaleX(1);
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 18px;
}

.balance-pair {
  display: flex;
  align-items: center;
  gap: 18px;
}

.btn-checkin {
  min-width: 64px;
  padding: 7px 14px;
  border: 1px solid var(--color-line-strong);
  border-radius: 999px;
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
  transition: transform var(--transition-base), border-color var(--transition-base);
}

.btn-checkin:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--color-ink);
}

.btn-checkin:disabled {
  color: var(--color-green);
  cursor: default;
}

.plan-badge {
  padding: 5px 10px;
  border: 1px solid var(--color-line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.64);
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.user-menu {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 3px 0 3px 3px;
  border: 0;
  background: transparent;
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 700;
}

.user-menu-wrap {
  position: relative;
}

.user-popover {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 210px;
  padding: 10px;
  display: grid;
  gap: 6px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(18px);
}

.user-popover-head {
  padding: 8px 9px 10px;
  display: grid;
  gap: 2px;
  border-bottom: 1px solid var(--color-line);
}

.user-popover-head strong {
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 13px;
}

.user-popover-head span {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
}

.user-popover a,
.logout-action {
  min-height: 34px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
  text-align: left;
  text-decoration: none;
}

.user-popover a:hover,
.logout-action:hover {
  background: var(--color-paper-soft);
  color: var(--color-ink);
}

.logout-action {
  color: var(--color-red);
}

.avatar {
  width: 31px;
  height: 31px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #262626, #76766e);
  color: #fff;
  font-size: 12px;
  font-weight: 900;
}

.chevron {
  color: var(--color-soft);
  font-size: 15px;
  line-height: 1;
}

.mobile-tabs {
  display: none;
}

.checkin-toast {
  position: fixed;
  top: 84px;
  left: 50%;
  z-index: 200;
  padding: 12px 22px;
  border: 1px solid rgba(63, 140, 104, 0.26);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--shadow-md);
  color: var(--color-green);
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 800;
  transform: translateX(-50%);
}

.toast-out {
  opacity: 0;
  transform: translate(-50%, -8px);
  transition: opacity var(--transition-base), transform var(--transition-base);
}

@media (max-width: 1120px) {
  .navbar-inner {
    grid-template-columns: auto 1fr auto;
    padding: 0 20px;
  }

  .nav-links {
    gap: 20px;
  }

  .btn-checkin,
  .plan-badge,
  .brand-subtitle {
    display: none;
  }
}

@media (max-width: 760px) {
  .navbar {
    position: relative;
  }

  .navbar-inner {
    min-height: 62px;
    grid-template-columns: 1fr auto;
    padding: 0 16px;
  }

  .nav-links {
    display: none;
  }

  .navbar-actions {
    gap: 10px;
  }

  .balance-pair {
    gap: 10px;
  }

  .username-text,
  .chevron {
    display: none;
  }

  .mobile-tabs {
    position: fixed;
    left: 12px;
    right: 12px;
    bottom: 12px;
    z-index: 120;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
    padding: 5px;
    border: 1px solid rgba(207, 212, 203, 0.84);
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.88);
    box-shadow: var(--shadow-lg);
    backdrop-filter: blur(18px);
  }

  .mobile-tab {
    min-height: 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 0;
    border-radius: 17px;
    background: transparent;
    color: var(--color-muted);
    font-family: var(--font-ui);
    font-size: 12px;
    font-weight: 800;
    text-decoration: none;
  }

  .mobile-tab--active {
    background: var(--color-ink);
    color: #fff;
  }

  .mobile-tab-button:disabled {
    color: var(--color-green);
  }
}
</style>
