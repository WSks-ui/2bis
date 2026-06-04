<template>
  <el-header class="navbar">
    <div class="navbar-left">
      <router-link to="/" class="site-name">AI图片生成</router-link>
      <el-menu
        mode="horizontal"
        :default-active="activeMenu"
        :ellipsis="false"
        class="navbar-menu"
        router
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/recharge">充值</el-menu-item>
        <el-menu-item index="/history">历史</el-menu-item>
      </el-menu>
    </div>
    <div class="navbar-right">
      <span class="navbar-username">{{ userStore.username }}</span>
      <PointsDisplay :balance="pointsStore.balance" />
      <el-tag v-if="userStore.isMember" type="warning" size="small" class="member-tag">
        会员 {{ formatExpireDate }}
      </el-tag>
      <el-button type="danger" size="small" @click="userStore.logout">
        退出登录
      </el-button>
    </div>
  </el-header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { usePointsStore } from '../stores/points'
import PointsDisplay from './PointsDisplay.vue'

const route = useRoute()
const userStore = useUserStore()
const pointsStore = usePointsStore()

const activeMenu = computed(() => route.path)

const formatExpireDate = computed(() => {
  if (!userStore.memberExpireAt) return ''
  const d = new Date(userStore.memberExpireAt)
  return d.toLocaleDateString('zh-CN')
})
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  height: 60px;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.site-name {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
  text-decoration: none;
  white-space: nowrap;
}

.navbar-menu {
  border-bottom: none !important;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.navbar-username {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.member-tag {
  white-space: nowrap;
}
</style>
