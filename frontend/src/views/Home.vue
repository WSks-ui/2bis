<template>
  <div class="home-page">
    <NavBar />
    <div class="home-content">
      <GenerateForm />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'
import GenerateForm from '../components/GenerateForm.vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

onMounted(() => {
  userStore.fetchUserInfo()
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.home-content {
  padding: 40px 20px;
}
</style>
