<template>
  <div class="reference-panel" :class="{ collapsed: isCollapsed }">
    <div class="panel-header" @click="toggleCollapse">
      <h3 class="title-chinese">📚 参考资料</h3>
      <span class="reference-count">{{ references.length }} 篇文档</span>
      <span class="collapse-icon">{{ isCollapsed ? '▶' : '▼' }}</span>
    </div>
    
    <div v-show="!isCollapsed" class="panel-content">
      <div v-if="references.length === 0" class="empty-references">
        <div class="empty-icon">书</div>
        <p>暂无参考资料</p>
        <p class="text-muted text-small">发送问题后将显示相关文档</p>
      </div>
      
      <div v-else class="reference-list">
        <div
          v-for="(ref, index) in references"
          :key="index"
          class="reference-item"
          :class="{ expanded: expandedIndex === index }"
        >
          <div class="reference-header" @click="toggleExpand(index)">
            <div class="reference-index-wrapper">
              <span class="reference-index">{{ index + 1 }}</span>
              <span v-if="ref.type" class="reference-type">{{ ref.type === 'bm25' ? '关键词' : '语义' }}</span>
            </div>
            <div class="reference-scores">
              <span v-if="ref.rrf_score" class="score-tag">
                RRF: {{ (ref.rrf_score * 100).toFixed(1) }}
              </span>
              <span v-if="ref.rerank_score" class="score-tag score-rerank">
                重排: {{ (ref.rerank_score * 100).toFixed(1) }}%
              </span>
              <span v-if="ref.distance !== undefined" class="score-tag score-distance">
                相似度: {{ ((1 - ref.distance) * 100).toFixed(1) }}%
              </span>
            </div>
            <span class="expand-icon">{{ expandedIndex === index ? '▼' : '▶' }}</span>
          </div>
          
          <div class="reference-body">
            <p class="reference-content">{{ ref.content }}</p>
            <div v-if="ref.metadata" class="reference-metadata">
              <span v-if="ref.metadata.source" class="metadata-item">
                📖 {{ ref.metadata.source }}
              </span>
            </div>
          </div>
          
          <div v-if="expandedIndex === index" class="reference-expanded">
            <div class="expanded-header">
              <span class="expanded-title">完整内容</span>
            </div>
            <p class="expanded-content">{{ ref.content }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { Reference } from '@/types'

const store = useChatStore()
const isCollapsed = ref(false)
const expandedIndex = ref<number | null>(null)

const references = computed<Reference[]>(() => {
  if (!store.currentSession?.messages.length) return []
  const lastMessage = store.currentSession.messages[store.currentSession.messages.length - 1]
  return lastMessage.role === 'assistant' ? (lastMessage.references || []) : []
})

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function toggleExpand(index: number) {
  expandedIndex.value = expandedIndex.value === index ? null : index
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

.reference-count {
  font-size: 12px;
  color: var(--color-accent);
  margin-right: 12px;
}

.collapse-icon {
  font-size: 12px;
  color: var(--color-ink-faint);
}

.panel-content {
  padding: 16px 20px;
  max-height: 300px;
  overflow-y: auto;
}

.empty-references {
  text-align: center;
  padding: 30px;
  color: var(--color-ink-faint);
}

.empty-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-accent) 0%, var(--color-accent-light) 100%);
  color: white;
  font-family: var(--font-family-chinese);
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
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
  overflow: hidden;
  transition: all 0.2s ease;
}

.reference-item:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-soft);
}

.reference-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: rgba(139, 115, 85, 0.05);
  cursor: pointer;
}

.reference-index-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
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
  font-weight: 600;
}

.reference-type {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(139, 115, 85, 0.1);
  color: var(--color-ink-light);
}

.reference-scores {
  display: flex;
  gap: 6px;
}

.score-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(139, 115, 85, 0.1);
  color: var(--color-ink-light);
}

.score-rerank {
  background: rgba(76, 175, 80, 0.15);
  color: #4caf50;
}

.score-distance {
  background: rgba(33, 150, 243, 0.15);
  color: #2196f3;
}

.expand-icon {
  font-size: 10px;
  color: var(--color-ink-faint);
  transition: transform 0.2s ease;
}

.reference-body {
  padding: 12px;
}

.reference-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-ink-black);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.reference-metadata {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.metadata-item {
  font-size: 12px;
  color: var(--color-ink-faint);
}

.reference-expanded {
  border-top: 1px dashed rgba(139, 115, 85, 0.2);
  background: rgba(139, 115, 85, 0.03);
}

.expanded-header {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(139, 115, 85, 0.1);
}

.expanded-title {
  font-size: 12px;
  color: var(--color-accent);
  font-weight: 500;
}

.expanded-content {
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-ink-black);
  margin: 0;
  white-space: pre-wrap;
}
</style>
