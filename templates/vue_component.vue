<template>
  <div class="component-name">
    <!-- 组件内容 -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

// ✅ 正确：不直接解构store，保持响应式
const store = useSomeStore()

// 响应式状态
const isLoading = ref(false)
const error = ref<string | null>(null)

// 计算属性
const computedValue = computed(() => {
  return store.someValue
})

// 方法
const handleClick = () => {
  // ✅ 正确：通过store访问状态
  store.updateValue('new value')
}

// 生命周期
onMounted(() => {
  // 初始化逻辑
})

onUnmounted(() => {
  // 清理逻辑
})
</script>

<style scoped>
.component-name {
  /* 样式 */
}
</style>