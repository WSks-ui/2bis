<template>
  <header class="navbar" :class="{ 'navbar--menu-open': userMenuOpen }">
    <div class="navbar-inner">
      <router-link to="/" class="brand" aria-label="2Bis 创作台">
        <span class="brand-word">2Bis</span>
        <span class="brand-subtitle">AI Image Studio</span>
      </router-link>

      <nav class="nav-links" aria-label="主导航">
        <router-link to="/" class="nav-link" active-class="nav-link--active" data-spotlight="off">创作台</router-link>
        <router-link to="/studio" class="nav-link" active-class="nav-link--active" data-spotlight="off">Studio</router-link>
        <router-link to="/history" class="nav-link" active-class="nav-link--active" data-spotlight="off">历史记录</router-link>
        <router-link to="/plans" class="nav-link" active-class="nav-link--active" data-spotlight="off">计划订阅</router-link>
      </nav>

      <div class="navbar-actions">
        <button
          class="btn-checkin"
          :class="{ 'btn-checkin-done': !checkinAvailable, 'btn-checkin-loading': checkinLoading }"
          :disabled="!checkinAvailable || checkinLoading"
          :aria-busy="checkinLoading"
          @click="doCheckin"
          data-spotlight="off"
        >
          <span class="checkin-dot" aria-hidden="true"></span>
          <span>{{ checkinLabel }}</span>
        </button>

        <div class="balance-pair" aria-label="当前可用额度">
          <PointsDisplay :balance="pointsStore.freePoints" label="体验积分" variant="experience" spotlight="off" />
          <PointsDisplay :balance="pointsStore.monthlyQuotaRemaining" label="订阅额度" variant="quota" spotlight="off" />
        </div>

        <span v-if="pointsStore.planLabel" class="plan-badge">{{ pointsStore.planLabel }}</span>

        <div class="user-menu-wrap">
          <button
            class="user-menu"
            title="账户菜单"
            aria-haspopup="menu"
            :aria-expanded="userMenuOpen"
            @click.stop="toggleUserMenu"
            data-spotlight="off"
          >
            <span class="avatar">{{ avatarText }}</span>
            <span class="username-text">{{ userStore.username || 'User' }}</span>
            <span class="chevron" :class="{ 'chevron--open': userMenuOpen }">⌄</span>
          </button>

          <Transition name="modal-pop">
          <div v-if="userMenuOpen" class="user-popover" role="menu" @click.stop>
            <div class="user-popover-head">
              <strong>{{ userStore.username || '未命名用户' }}</strong>
              <span>{{ pointsStore.planLabel || '未订阅' }}</span>
            </div>
            <router-link to="/plans" role="menuitem" @click="userMenuOpen = false">
              <span class="menu-icon">P</span>
              管理订阅
            </router-link>
            <router-link to="/studio" role="menuitem" @click="userMenuOpen = false">
              <span class="menu-icon">S</span>
              Studio 工作区
            </router-link>
            <router-link to="/history" role="menuitem" @click="userMenuOpen = false">
              <span class="menu-icon">H</span>
              查看历史
            </router-link>
            <router-link v-if="userStore.isAdmin" to="/admin/api-keys" role="menuitem" @click="userMenuOpen = false">
              <span class="menu-icon">K</span>
              API Key 控制台
            </router-link>
            <button type="button" class="logout-action" role="menuitem" @click="logout">
              <span class="menu-icon">Q</span>
              退出登录
            </button>
          </div>
          </Transition>
        </div>
      </div>
    </div>

    <nav class="mobile-tabs" aria-label="移动导航">
      <router-link to="/" class="mobile-tab" active-class="mobile-tab--active">创作</router-link>
      <router-link to="/studio" class="mobile-tab" active-class="mobile-tab--active">Studio</router-link>
      <router-link to="/history" class="mobile-tab" active-class="mobile-tab--active">历史</router-link>
      <router-link to="/plans" class="mobile-tab" active-class="mobile-tab--active">订阅</router-link>
    </nav>

    <Transition name="modal-pop">
    <div v-if="checkinResult" class="checkin-toast" :class="{ 'toast-out': toastHiding }">
      签到成功，第 {{ checkinResult.day_number }} 天，+{{ checkinResult.reward }} 体验积分
    </div>
    </Transition>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from '../services/toast'
import { useUserStore } from '../stores/user'
import { usePointsStore } from '../stores/points'
import PointsDisplay from './PointsDisplay.vue'
import api from '../api'
import { warmPlansConfig } from '../services/plansCache'

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
  if (checkinLoading.value) return '签到中'
  if (!checkinAvailable.value && checkinDay.value > 0) return '已签到'
  return '签到'
})

const avatarText = computed(() => {
  const name = userStore.username || '2B'
  return name.slice(0, 1).toUpperCase()
})

onMounted(async () => {
  window.addEventListener('click', closeUserMenu)
  warmPlansConfig()
  await Promise.allSettled([
    userStore.refreshUserInfoQuietly(),
    refreshCheckinStatus()
  ])
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeUserMenu)
  clearTimeout(toastTimer)
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

async function refreshCheckinStatus() {
  try {
    const res = await api.get('/auth/checkin/status')
    checkinAvailable.value = res.data.checkin_available
    checkinDay.value = res.data.consecutive_days
  } catch (_) {}
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
  background:
    linear-gradient(180deg, rgba(255, 255, 252, 0.94), rgba(251, 251, 248, 0.82)),
    rgba(251, 251, 248, 0.86);
  backdrop-filter: blur(22px);
  animation: nav-drop 520ms var(--ease-out-soft) both;
  transition: border-color var(--transition-base), box-shadow var(--transition-base), background var(--transition-base);
}

.navbar--menu-open {
  border-color: rgba(23, 23, 23, 0.08);
  box-shadow: 0 16px 46px rgba(23, 23, 23, 0.07);
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
  transition: transform var(--transition-base), color var(--transition-base);
}

.brand:hover {
  transform: translateY(-1px) skewX(-3deg);
}

.brand-word {
  font-family: var(--font-heading);
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.08em;
  font-style: italic;
  transition: letter-spacing var(--transition-base);
}

.brand:hover .brand-word {
  letter-spacing: -0.1em;
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
  align-items: center;
  justify-content: center;
  align-self: stretch;
  gap: 34px;
}

.nav-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  min-height: 36px;
  padding: 7px 16px;
  border-radius: 999px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.15;
  text-decoration: none;
  transition:
    color var(--transition-base),
    background var(--transition-base),
    transform var(--transition-base),
    box-shadow var(--transition-base);
}

.nav-link::after {
  content: '';
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 4px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, var(--color-ink), transparent);
  transform: scaleX(0);
  transform-origin: center;
  transition: transform var(--transition-base);
}

.nav-link:hover,
.nav-link--active {
  color: var(--color-ink);
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.62);
  transform: translateY(-1px);
}

.nav-link:hover::after {
  transform: scaleX(0.48);
}

.nav-link--active {
  background:
    linear-gradient(135deg, rgba(23, 23, 23, 0.07), rgba(255, 255, 255, 0.66)),
    rgba(255, 255, 255, 0.54);
  box-shadow: inset 0 0 0 1px rgba(23, 23, 23, 0.04), 0 8px 20px rgba(23, 23, 23, 0.05);
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
  gap: 10px;
}

.btn-checkin {
  position: relative;
  overflow: hidden;
  min-width: 82px;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 7px 14px 7px 10px;
  border: 1px solid var(--color-line-strong);
  border-radius: 999px;
  background:
    linear-gradient(135deg, rgba(63, 140, 104, 0.1), rgba(255, 255, 255, 0.7)),
    #fff;
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
  transition:
    transform var(--transition-base),
    border-color var(--transition-base),
    box-shadow var(--transition-base),
    opacity var(--transition-base),
    background var(--transition-base);
}

.checkin-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--color-green);
  box-shadow: 0 0 0 5px rgba(63, 140, 104, 0.12);
  transition: transform var(--transition-base), opacity var(--transition-base);
}

.btn-checkin:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(63, 140, 104, 0.36);
  box-shadow: 0 12px 24px rgba(63, 140, 104, 0.13);
}

.btn-checkin:hover:not(:disabled) .checkin-dot {
  transform: scale(1.16);
}

.btn-checkin:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
}

.btn-checkin:disabled {
  color: var(--color-green);
  cursor: default;
}

.btn-checkin-done {
  background: rgba(255, 255, 255, 0.64);
}

.btn-checkin-done .checkin-dot {
  opacity: 0.42;
  box-shadow: none;
}

.btn-checkin-loading .checkin-dot {
  animation: checkin-breathe 820ms ease-in-out infinite;
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
  animation: badge-in 420ms var(--ease-out-soft) both;
}

.user-menu {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 40px;
  padding: 4px 10px 4px 4px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.46);
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 700;
  transition:
    transform var(--transition-base),
    color var(--transition-base),
    border-color var(--transition-base),
    background var(--transition-base),
    box-shadow var(--transition-base);
}

.user-menu:hover {
  border-color: rgba(23, 23, 23, 0.08);
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 10px 24px rgba(23, 23, 23, 0.06);
  transform: translateY(-1px);
}

.user-menu-wrap {
  position: relative;
}

.user-popover {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 236px;
  padding: 10px;
  display: grid;
  gap: 6px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(18px);
  transform-origin: 90% 0;
}

.user-popover-head {
  padding: 10px 10px 12px;
  display: grid;
  gap: 2px;
  border-bottom: 1px solid var(--color-line);
  background:
    radial-gradient(circle at 10% 20%, rgba(60, 110, 232, 0.1), transparent 34%),
    var(--color-paper-soft);
  border-radius: calc(var(--radius-lg) - 8px);
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
  min-height: 38px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
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
  transition:
    background var(--transition-base),
    color var(--transition-base),
    transform var(--transition-base);
}

.user-popover a:hover,
.logout-action:hover {
  background: var(--color-paper-soft);
  color: var(--color-ink);
  transform: translateX(2px);
}

.logout-action {
  color: var(--color-red);
}

.menu-icon {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(23, 23, 23, 0.06);
  color: var(--color-ink);
  font-family: var(--font-heading);
  font-size: 10px;
  font-weight: 900;
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
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

.user-menu:hover .avatar {
  transform: rotate(-6deg) scale(1.04);
  box-shadow: 0 8px 20px rgba(23, 23, 23, 0.14);
}

.chevron {
  color: var(--color-soft);
  font-size: 15px;
  line-height: 1;
  transition: transform var(--transition-base), color var(--transition-base);
}

.chevron--open {
  color: var(--color-ink);
  transform: rotate(180deg);
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
    transition: background var(--transition-base), color var(--transition-base), transform var(--transition-base);
  }

  .mobile-tab--active {
    background: var(--color-ink);
    color: #fff;
    transform: translateY(-1px);
  }

  .mobile-tab-button:disabled {
    color: var(--color-green);
  }
}

@keyframes nav-drop {
  from {
    opacity: 0;
    transform: translate3d(0, -12px, 0);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes badge-in {
  from {
    opacity: 0;
    transform: translate3d(0, -4px, 0) scale(0.96);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
  }
}

@keyframes checkin-breathe {
  0%, 100% {
    opacity: 0.48;
    transform: scale(0.82);
  }

  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}
</style>
