<template>
  <div class="chat-container">
    <ChatSidebar @toggle-settings="showSettings = true" />
    <div class="main-content">
      <ChatArea />
      <ReferencePanel />
    </div>
    <SettingsPanel :is-visible="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChatSidebar from './components/ChatSidebar.vue'
import ChatArea from './components/ChatArea.vue'
import ReferencePanel from './components/ReferencePanel.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const showSettings = ref(false)
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
}
</style>
