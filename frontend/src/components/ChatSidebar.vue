<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="title-chinese">苏轼文化数字人</h1>
      <p class="subtitle">东坡居士 · 诗词问答</p>
    </div>
    
    <div class="new-chat-btn">
      <button class="classic-btn classic-btn-primary" @click="createNewChat">
        <span>+</span> 新对话
      </button>
    </div>
    
    <div class="chat-list">
      <div
        v-for="session in sortedSessions"
        :key="session.id"
        class="chat-item"
        :class="{ active: session.id === currentSessionId }"
        @click="selectSession(session.id)"
      >
        <div class="chat-icon">
          <span class="icon-text">苏</span>
        </div>
        <div class="chat-info">
          <h3 class="chat-title">{{ session.title }}</h3>
          <p class="chat-time">{{ formatTime(session.createdAt) }}</p>
        </div>
        <button class="delete-btn" @click.stop="deleteSession(session.id)">
          <span>×</span>
        </button>
      </div>
      
      <div v-if="sortedSessions.length === 0" class="empty-state">
        <div class="empty-icon">📜</div>
        <p>暂无对话</p>
        <p class="text-muted text-small">点击上方按钮开始新对话</p>
      </div>
    </div>
    
    <div class="sidebar-footer">
      <button class="settings-toggle" @click="toggleSettings">
        <span>⚙️</span> 设置
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const { sortedSessions, currentSessionId, createSession, selectSession, deleteSession } = store

const emit = defineEmits<{
  toggleSettings: []
}>()

function createNewChat() {
  createSession()
}

function formatTime(date: Date): string {
  const now = new Date()
  const diff = now.getTime() - new Date(date).getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return new Date(date).toLocaleDateString('zh-CN')
}

function toggleSettings() {
  emit('toggleSettings')
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  background: var(--color-paper-warm);
  border-right: 1px solid rgba(139, 115, 85, 0.15);
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.sidebar-header {
  text-align: center;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(139, 115, 85, 0.15);
  margin-bottom: 20px;
}

.sidebar-header h1 {
  font-size: 18px;
  margin-bottom: 4px;
  color: var(--color-ink-black);
}

.subtitle {
  font-size: 12px;
  color: var(--color-ink-faint);
  font-style: italic;
}

.new-chat-btn {
  margin-bottom: 20px;
}

.new-chat-btn button {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  font-size: 14px;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
}

.chat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
}

.chat-item:hover {
  background: rgba(139, 115, 85, 0.08);
}

.chat-item.active {
  background: rgba(139, 115, 85, 0.15);
}

.chat-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-accent) 0%, var(--color-accent-light) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-text {
  color: white;
  font-family: var(--font-family-chinese);
  font-size: 14px;
  font-weight: 600;
}

.chat-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.chat-title {
  font-size: 14px;
  color: var(--color-ink-black);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-time {
  font-size: 12px;
  color: var(--color-ink-faint);
}

.delete-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--color-ink-faint);
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.2s ease;
}

.chat-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(181, 71, 71, 0.1);
  color: var(--color-error);
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-ink-faint);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 14px;
  margin-bottom: 4px;
}

.sidebar-footer {
  padding-top: 16px;
  border-top: 1px solid rgba(139, 115, 85, 0.15);
}

.settings-toggle {
  width: 100%;
  padding: 10px;
  border: none;
  background: transparent;
  color: var(--color-ink-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.settings-toggle:hover {
  background: rgba(139, 115, 85, 0.08);
}
</style>
