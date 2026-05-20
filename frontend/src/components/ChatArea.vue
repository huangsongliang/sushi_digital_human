<template>
  <div class="chat-area">
    <div v-if="!store.currentSession" class="welcome-screen">
      <div class="welcome-content">
        <div class="welcome-icon">
          <span class="poem-icon">知</span>
        </div>
        <h1 class="title-chinese">企业级智能文档问答平台</h1>
        <p class="welcome-desc">智能管理企业知识库，精准回答问题</p>
        <div class="feature-list">
          <div class="feature-item">📚 智能问答</div>
          <div class="feature-item">📖 文档管理</div>
          <div class="feature-item">🎨 智能检索</div>
        </div>
        <button class="classic-btn classic-btn-primary" @click="startChat">
          开始对话
        </button>
      </div>
    </div>

    <div v-else class="chat-content">
      <div class="chat-header">
        <h2 class="title-chinese">{{ store.currentSession.title }}</h2>
        <div class="header-actions">
          <button class="header-btn" @click="clearChat">
            <span>🗑️</span>
          </button>
        </div>
      </div>

      <div ref="messagesContainer" class="messages-container">
        <div
          v-for="(message, index) in store.currentSession.messages"
          :key="message.id"
          class="message-wrapper"
          :class="{ 'user-message': message.role === 'user' }"
          :style="{ animationDelay: `${index * 0.05}s` }"
        >
          <div class="message-bubble">
            <div class="message-avatar">
              <span v-if="message.role === 'user'">你</span>
              <span v-else>智</span>
            </div>
            <div class="message-content">
              <p class="message-text">{{ message.content }}</p>
              <div v-if="message.status && message.status !== 'completed'" class="message-status">
                <span v-if="message.status === 'pending'" class="status-badge status-pending">排队中...</span>
                <span v-else-if="message.status === 'processing'" class="status-badge status-processing">处理中...</span>
                <span v-else-if="message.status === 'failed'" class="status-badge status-failed">失败</span>
              </div>
              <div class="message-meta">
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="store.isStreaming" class="typing-indicator">
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span class="typing-text">正在思考...</span>
        </div>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <textarea
            v-model="inputMessage"
            class="classic-input message-input"
            placeholder="请输入您的问题..."
            rows="2"
            @keydown.enter.exact.prevent="handleSend"
          ></textarea>
          <button
            class="send-btn"
            :disabled="!inputMessage.trim() || store.isStreaming"
            @click="handleSend"
          >
            <span>发送</span>
          </button>
        </div>
        <div class="input-actions">
          <label class="checkbox-label">
            <input
              type="checkbox"
              :checked="store.settings.useRag"
              @change="store.updateSettings({ useRag: !store.settings.useRag })"
            />
            <span>使用知识库</span>
          </label>
          <span class="mode-indicator">
            <span class="mode-badge">异步模式</span>
            <span class="mode-hint">发送后可继续提问</span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

console.log('[ChatArea] Current session:', store.currentSession)
console.log('[ChatArea] Current session ID:', store.currentSession?.id)
console.log('[ChatArea] Messages count:', store.currentSession?.messages.length)

function startChat() {
  console.log('[ChatArea] startChat called')
  store.createSession()
  console.log('[ChatArea] After createSession, current session:', store.currentSession)
}

function handleSend() {
  if (!inputMessage.value.trim() || store.isStreaming) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  console.log('[ChatArea] Sending message:', message)
  console.log('[ChatArea] Current session before send:', store.currentSession?.id)

  // 默认使用异步模式
  store.sendMessageAsync(message)

  nextTick(() => {
    scrollToBottom()
  })
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function clearChat() {
  if (store.currentSession) {
    store.currentSession.messages = []
    store.currentSession.title = '新对话'
  }
}

watch(() => {
  return store.currentSession ? store.currentSession.messages.length : 0
}, () => {
  nextTick(scrollToBottom)
})
</script>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-paper);
}

.welcome-screen {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-paper) 0%, var(--color-paper-warm) 100%);
}

.welcome-content {
  text-align: center;
  padding: 40px;
}

.welcome-icon {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-accent) 0%, var(--color-accent-light) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}

.poem-icon {
  color: white;
  font-family: var(--font-family-chinese);
  font-size: 48px;
  font-weight: 600;
}

.welcome-content h1 {
  font-size: 28px;
  margin-bottom: 12px;
  color: var(--color-ink-black);
}

.welcome-desc {
  font-size: 16px;
  color: var(--color-ink-light);
  margin-bottom: 32px;
}

.feature-list {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 32px;
}

.feature-item {
  font-size: 14px;
  color: var(--color-ink-light);
  padding: 8px 16px;
  background: rgba(139, 115, 85, 0.08);
  border-radius: var(--radius-md);
}

.welcome-content button {
  padding: 12px 32px;
  font-size: 16px;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--color-paper-warm);
  border-bottom: 1px solid rgba(139, 115, 85, 0.15);
}

.chat-header h2 {
  font-size: 16px;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.header-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.header-btn:hover {
  background: rgba(181, 71, 71, 0.1);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-wrapper {
  display: flex;
  animation: fadeIn 0.3s ease forwards;
}

.message-wrapper.user-message {
  justify-content: flex-end;
}

.message-bubble {
  display: flex;
  gap: 12px;
  max-width: 70%;
}

.user-message .message-bubble {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-accent) 0%, var(--color-accent-light) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: white;
  font-family: var(--font-family-chinese);
  font-size: 14px;
  font-weight: 600;
}

.user-message .message-avatar {
  background: linear-gradient(135deg, var(--color-ink-gray) 0%, var(--color-ink-light) 100%);
}

.message-content {
  background: var(--color-paper-warm);
  border: 1px solid rgba(139, 115, 85, 0.15);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  box-shadow: var(--shadow-soft);
}

.user-message .message-content {
  background: var(--color-accent);
  border-color: var(--color-accent);
}

.message-text {
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 8px;
  color: var(--color-ink-black);
}

.user-message .message-text {
  color: white;
}

.message-meta {
  display: flex;
  justify-content: flex-end;
}

.message-time {
  font-size: 11px;
  color: var(--color-ink-faint);
}

.user-message .message-time {
  color: rgba(255, 255, 255, 0.7);
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--color-paper-warm);
  border: 1px solid rgba(139, 115, 85, 0.15);
  border-radius: var(--radius-lg);
  max-width: 200px;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: typingDot 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingDot {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.typing-text {
  font-size: 14px;
  color: var(--color-ink-light);
}

.input-area {
  padding: 16px 20px;
  background: var(--color-paper-warm);
  border-top: 1px solid rgba(139, 115, 85, 0.15);
}

.input-wrapper {
  display: flex;
  gap: 12px;
}

.message-input {
  flex: 1;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
}

.send-btn {
  padding: 12px 24px;
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family-chinese);
  transition: all 0.2s ease;
  align-self: flex-end;
}

.send-btn:hover:not(:disabled) {
  background: var(--color-accent-light);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-ink-light);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--color-accent);
}

.message-status {
  margin-bottom: 8px;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
}

.status-pending {
  background: rgba(255, 193, 7, 0.15);
  color: #856404;
}

.status-processing {
  background: rgba(33, 150, 243, 0.15);
  color: #1565c0;
}

.status-failed {
  background: rgba(244, 67, 54, 0.15);
  color: #c62828;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.mode-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-badge {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(33, 150, 243, 0.15);
  color: #1565c0;
  border-radius: var(--radius-sm);
}

.mode-hint {
  font-size: 11px;
  color: var(--color-ink-faint);
}
</style>
