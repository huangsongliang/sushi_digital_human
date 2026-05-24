<template>
  <div class="chat-container">
    <!-- 移动端遮罩 -->
    <div v-if="sidebarOpen" class="mobile-overlay" @click="sidebarOpen = false"></div>

    <ChatSidebar
      :class="{ 'sidebar-open': sidebarOpen }"
      @toggle-settings="showSettings = true"
      @close-sidebar="sidebarOpen = false"
    />

    <div class="main-content">
      <!-- 移动端汉堡菜单按钮 -->
      <button class="hamburger-btn" @click.stop="sidebarOpen = !sidebarOpen">
        <span>☰</span>
      </button>
      <ChatArea />
      <ReferencePanel />
    </div>
    <SettingsPanel :is-visible="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChatSidebar from './ChatSidebar.vue'
import ChatArea from './ChatArea.vue'
import ReferencePanel from './ReferencePanel.vue'
import SettingsPanel from './SettingsPanel.vue'

const showSettings = ref(false)
const sidebarOpen = ref(false)
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.hamburger-btn {
  display: none;
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 500;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(139, 115, 85, 0.2);
  background: var(--color-paper-warm);
  border-radius: var(--radius-md);
  font-size: 20px;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  color: var(--color-ink-black);
}

.mobile-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 998;
}

/* 平板 */
@media (max-width: 1024px) {
  .chat-container :deep(.sidebar) {
    width: 240px;
  }
}

/* 手机 */
@media (max-width: 768px) {
  .hamburger-btn {
    display: flex;
  }

  .mobile-overlay {
    display: block;
  }

  .chat-container :deep(.sidebar) {
    position: fixed;
    left: -280px;
    top: 0;
    bottom: 0;
    width: 280px;
    z-index: 999;
    transition: left 0.3s ease;
  }

  .chat-container :deep(.sidebar.sidebar-open) {
    left: 0;
  }
}
</style>
