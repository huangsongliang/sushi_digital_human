<template>
  <div class="reference-panel" :class="{ collapsed: isCollapsed }">
    <div class="panel-header" @click="toggleCollapse">
      <h3 class="title-chinese">📚 参考资料</h3>
      <span class="collapse-icon">{{ isCollapsed ? '▶' : '▼' }}</span>
    </div>
    
    <div v-show="!isCollapsed" class="panel-content">
      <div v-if="references.length === 0" class="empty-references">
        <p>暂无参考资料</p>
        <p class="text-muted text-small">发送问题后将显示相关文档</p>
      </div>
      
      <div v-else class="reference-list">
        <div
          v-for="(ref, index) in references"
          :key="index"
          class="reference-item"
        >
          <div class="reference-header">
            <span class="reference-index">{{ index + 1 }}</span>
            <span class="reference-similarity">
              相似度: {{ (1 - ref.distance) * 100 | numberFormat }}%
            </span>
          </div>
          <p class="reference-content">{{ ref.content }}</p>
          <div v-if="ref.metadata" class="reference-metadata">
            <span v-if="ref.metadata.source" class="metadata-item">
              📖 {{ ref.metadata.source }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const isCollapsed = ref(false)

const references = computed(() => {
  if (!store.currentSession?.messages.length) return []
  const lastMessage = store.currentSession.messages[store.currentSession.messages.length - 1]
  return lastMessage.role === 'assistant' ? (lastMessage.references || []) : []
})

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.reference-panel {
  background: var(--color-paper-warm);
  border-top: 1px solid rgba(139, 115, 85, 0.15);
  transition: all 0.3s ease;
}

.reference-panel.collapsed {
  max-height: 40px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  cursor: pointer;
  background: rgba(139, 115, 85, 0.08);
}

.panel-header h3 {
  font-size: 14px;
  margin: 0;
  color: var(--color-ink-black);
}

.collapse-icon {
  font-size: 12px;
  color: var(--color-ink-faint);
}

.panel-content {
  padding: 16px 20px;
  max-height: 200px;
  overflow-y: auto;
}

.empty-references {
  text-align: center;
  padding: 20px;
  color: var(--color-ink-faint);
}

.empty-references p {
  margin: 0 0 4px;
  font-size: 14px;
}

.reference-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reference-item {
  background: var(--color-paper);
  border: 1px solid rgba(139, 115, 85, 0.15);
  border-radius: var(--radius-md);
  padding: 12px;
}

.reference-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.reference-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-accent);
  color: white;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.reference-similarity {
  font-size: 12px;
  color: var(--color-accent);
}

.reference-content {
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-ink-black);
  margin: 0 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.reference-metadata {
  display: flex;
  gap: 8px;
}

.metadata-item {
  font-size: 12px;
  color: var(--color-ink-faint);
}
</style>
