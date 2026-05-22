<template>
  <div id="app">
    <ThemeToggle />
    <Notification />
    <router-view />
  </div>
</template>

<script setup lang="ts">
import ThemeToggle from './components/ThemeToggle.vue'
import Notification from './components/Notification.vue'
</script>

<style>
#app {
  height: 100vh;
  overflow: hidden;
}
</style>
