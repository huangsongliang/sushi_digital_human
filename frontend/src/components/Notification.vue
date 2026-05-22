<template>
  <div class="notification-container">
    <transition-group name="notification-list">
      <el-alert
        v-for="notification in store.notifications"
        :key="notification.id"
        :type="notification.type"
        :closable="true"
        :title="notification.title"
        :description="notification.message"
        show-icon
        @close="store.remove(notification.id)"
        class="notification-item"
      />
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { useNotificationStore } from '../stores/notification'

const store = useNotificationStore()
</script>

<style scoped>
.notification-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification-item {
  width: 350px;
  max-width: 90vw;
}

.notification-list-enter-active,
.notification-list-leave-active {
  transition: all 0.3s ease;
}

.notification-list-enter-from,
.notification-list-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
