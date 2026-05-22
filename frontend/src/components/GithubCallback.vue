<template>
  <div class="callback-container">
    <div class="loading-spinner">
      <div class="spinner"></div>
      <p v-if="!errorText">正在登录...</p>
      <p v-else class="error-text">{{ errorText }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const errorText = ref('')

onMounted(async () => {
  try {
    const urlParams = new URLSearchParams(window.location.search)
    const accessToken = urlParams.get('access_token')
    const refreshTokenVal = urlParams.get('refresh_token')

    if (accessToken) {
      authStore.accessToken = accessToken
      localStorage.setItem('access_token', accessToken)

      if (refreshTokenVal) {
        authStore.refreshToken = refreshTokenVal
        localStorage.setItem('refresh_token', refreshTokenVal)
      }

      await authStore.fetchUser()
      router.push('/')
    } else {
      errorText.value = '授权失败，正在返回登录页...'
      setTimeout(() => router.push('/login'), 2000)
    }
  } catch (err) {
    console.error('GitHub 登录失败:', err)
    errorText.value = '登录失败，正在返回...'
    setTimeout(() => router.push('/login'), 2000)
  }
})
</script>

<style scoped>
.callback-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-spinner p {
  color: white;
  font-size: 16px;
}

.error-text {
  color: #ffcdd2 !important;
}
</style>