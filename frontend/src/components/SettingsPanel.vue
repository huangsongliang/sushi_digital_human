<template>
  <div class="settings-panel" :class="{ visible: isVisible }">
    <div class="panel-overlay" @click="close"></div>

    <div class="panel-content">
      <div class="panel-header">
        <h2 class="title-chinese">设置</h2>
        <button class="close-btn" @click="close">
          <span>×</span>
        </button>
      </div>

      <div class="settings-section">
        <h3 class="section-title">检索设置</h3>

        <div class="setting-item">
          <label class="setting-label">
            <input
              type="checkbox"
              :checked="store.settings.useRag"
              @change="updateSetting('useRag', !store.settings.useRag)"
            />
            <span>启用知识库检索</span>
          </label>
          <p class="setting-desc">启用后，回答将基于知识库文档</p>
        </div>

        <div class="setting-item">
          <label class="setting-label">检索数量</label>
          <input
            type="range"
            :value="store.settings.topK"
            min="1"
            max="10"
            @input="updateSetting('topK', Number(($event.target as HTMLInputElement).value))"
            class="range-input"
          />
          <span class="range-value">{{ store.settings.topK }}</span>
          <p class="setting-desc">每次检索返回的文档数量</p>
        </div>
      </div>

      <div class="settings-section">
        <h3 class="section-title">模型设置</h3>

        <div class="setting-item">
          <label class="setting-label">温度参数</label>
          <input
            type="range"
            :value="store.settings.temperature"
            min="0"
            max="2"
            step="0.1"
            @input="updateSetting('temperature', Number(($event.target as HTMLInputElement).value))"
            class="range-input"
          />
          <span class="range-value">{{ store.settings.temperature.toFixed(1) }}</span>
          <p class="setting-desc">控制回答的随机性，值越大越随机</p>
        </div>
      </div>

      <div class="settings-section">
        <h3 class="section-title">关于</h3>
        <div class="about-info">
                <p><strong>版本:</strong> 1.0.0</p>
                <p><strong>主题:</strong> 企业级智能文档问答平台</p>
                <p><strong>描述:</strong> 基于RAG技术的企业知识库问答系统</p>
            </div>
      </div>

      <div class="panel-footer">
        <button class="classic-btn" @click="resetSettings">
          重置设置
        </button>
        <button class="classic-btn classic-btn-primary" @click="close">
          确定
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useChatStore } from '@/stores/chat'

defineProps<{
  isVisible: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const store = useChatStore()

function close() {
  emit('close')
}

function updateSetting(key: 'useRag' | 'topK' | 'temperature', value: boolean | number) {
  store.updateSettings({ [key]: value })
}

function resetSettings() {
  store.updateSettings({
    useRag: true,
    topK: 3,
    temperature: 0.7
  })
}
</script>

<style scoped>
.settings-panel {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: none;
}

.settings-panel.visible {
  display: block;
}

.settings-panel.visible .panel-overlay {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.panel-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
  z-index: 1001;
}

.settings-panel.visible .panel-overlay {
  opacity: 1;
  visibility: visible;
}

.panel-content {
  position: fixed;
  top: 0;
  right: 0;
  width: 300px;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
  z-index: 1002;
  background: #ffffff;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
  overflow-y: auto;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.panel-header h2 {
  font-size: 20px;
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: var(--color-ink-light);
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

.settings-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-ink-black);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(139, 115, 85, 0.15);
}

.setting-item {
  margin-bottom: 16px;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-ink-black);
  cursor: pointer;
  margin-bottom: 4px;
}

.setting-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: #667eea;
  cursor: pointer;
}

.setting-label input[type="checkbox"]:hover {
  transform: scale(1.1);
}

.setting-desc {
  font-size: 12px;
  color: var(--color-ink-faint);
  margin: 0 0 8px;
}

.range-input {
  width: 100%;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: #e8e8e8;
  border-radius: 4px;
  cursor: pointer;
  outline: none;
}

.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.4);
}

.range-input::-webkit-slider-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 3px 10px rgba(102, 126, 234, 0.5);
}

.range-input::-moz-range-track {
  width: 100%;
  height: 8px;
  background: #e8e8e8;
  border-radius: 4px;
  cursor: pointer;
}

.range-input::-moz-range-thumb {
  width: 18px;
  height: 18px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.4);
}

.range-value {
  display: inline-block;
  margin-left: 8px;
  font-size: 14px;
  color: var(--color-accent);
  font-weight: 600;
}

.about-info {
  font-size: 13px;
  color: var(--color-ink-light);
  line-height: 1.8;
}

.about-info strong {
  color: var(--color-ink-black);
}

.panel-footer {
  margin-top: auto;
  display: flex;
  gap: 12px;
}

.panel-footer button {
  flex: 1;
  padding: 10px;
}
</style>
