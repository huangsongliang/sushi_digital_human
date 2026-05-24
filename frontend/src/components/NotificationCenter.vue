<template>
  <div class="notification-center-page">
    <!-- 顶部栏 -->
    <header class="page-header">
      <button class="back-btn" @click="goBack">
        <span>←</span> 返回
      </button>
      <h1 class="page-title">通知中心</h1>
      <div class="header-actions">
        <button
          v-if="store.unreadCount > 0"
          class="action-btn"
          @click="handleMarkAllRead"
        >
          全部已读
        </button>
        <button
          v-if="store.persistentNotifications.length > 0"
          class="action-btn action-btn-danger"
          @click="handleClearAll"
        >
          清空
        </button>
      </div>
    </header>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <button
        v-for="filter in filters"
        :key="filter.key"
        class="filter-btn"
        :class="{ active: activeFilter === filter.key }"
        @click="activeFilter = filter.key"
      >
        {{ filter.label }}
        <span v-if="filter.key === 'unread'" class="filter-badge">
          {{ store.unreadCount }}
        </span>
      </button>
    </div>

    <!-- 通知列表 -->
    <div v-loading="store.loading" class="notification-list">
      <div
        v-for="notification in filteredNotifications"
        :key="notification.id"
        class="notification-card"
        :class="{ unread: !notification.is_read }"
        @click="handleCardClick(notification)"
      >
        <div class="card-left">
          <span class="type-icon">{{ typeIcon(notification.type) }}</span>
        </div>
        <div class="card-body">
          <div class="card-header">
            <h3 class="card-title">{{ notification.title }}</h3>
            <span class="card-time">{{ formatTime(notification.created_at) }}</span>
          </div>
          <p class="card-content">{{ notification.content }}</p>
          <div class="card-meta">
            <el-tag
              :type="tagType(notification.type)"
              size="small"
              effect="plain"
            >
              {{ typeLabel(notification.type) }}
            </el-tag>
            <span v-if="!notification.is_read" class="unread-dot"></span>
          </div>
        </div>
        <div class="card-actions">
          <button
            v-if="!notification.is_read"
            class="icon-btn"
            title="标记已读"
            @click.stop="handleMarkRead(notification.id)"
          >
            ✓
          </button>
          <button
            class="icon-btn icon-btn-delete"
            title="删除"
            @click.stop="handleDelete(notification.id)"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!store.loading && filteredNotifications.length === 0" class="empty-state">
        <div class="empty-icon">🔔</div>
        <p class="empty-title">暂无通知</p>
        <p class="empty-desc">
          {{ activeFilter === 'all' ? '你还没有任何通知消息' : '没有未读通知' }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useNotificationStore } from '@/stores/notification'
import type { ServerNotification, NotificationTypeEnum } from '@/api/notification'

const store = useNotificationStore()
const router = useRouter()

const activeFilter = ref<'all' | 'unread'>('all')

const filters = [
  { key: 'all' as const, label: '全部' },
  { key: 'unread' as const, label: '未读' },
]

const filteredNotifications = computed(() => {
  if (activeFilter.value === 'unread') {
    return store.persistentNotifications.filter(n => !n.is_read)
  }
  return store.persistentNotifications
})

onMounted(() => {
  store.fetchNotifications()
})

watch(activeFilter, () => {
  if (activeFilter.value === 'unread') {
    store.fetchNotifications(true)
  } else {
    store.fetchNotifications(false)
  }
})

function goBack() {
  router.push('/')
}

function typeIcon(type: NotificationTypeEnum): string {
  const icons: Record<string, string> = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌',
    document_update: '📄',
    system_alert: '🚨',
    chat_message: '💬',
  }
  return icons[type] || '📌'
}

function typeLabel(type: NotificationTypeEnum): string {
  const labels: Record<string, string> = {
    info: '信息',
    success: '成功',
    warning: '警告',
    error: '错误',
    document_update: '文档更新',
    system_alert: '系统告警',
    chat_message: '聊天消息',
  }
  return labels[type] || type
}

function tagType(type: NotificationTypeEnum): 'info' | 'success' | 'warning' | 'danger' | '' {
  const map: Record<string, 'info' | 'success' | 'warning' | 'danger'> = {
    info: 'info',
    success: 'success',
    warning: 'warning',
    error: 'danger',
    document_update: '',
    system_alert: 'danger',
    chat_message: 'info',
  }
  return map[type] || 'info'
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

function handleCardClick(notification: ServerNotification) {
  if (!notification.is_read) {
    store.markRead(notification.id)
  }
}

async function handleMarkRead(id: string) {
  await store.markRead(id)
}

async function handleDelete(id: string) {
  await store.deleteNotification(id)
}

async function handleMarkAllRead() {
  await store.markAllRead()
  store.toastSuccess('已全部标记为已读')
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定要清空所有通知吗？此操作不可恢复。', '确认清空', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await store.clearAll()
    store.toastSuccess('已清空所有通知')
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.notification-center-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-paper-warm);
}

.page-header {
  display: flex;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(139, 115, 85, 0.15);
  gap: 16px;
}

.back-btn {
  padding: 8px 14px;
  border: 1px solid rgba(139, 115, 85, 0.2);
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--color-ink-light);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: rgba(139, 115, 85, 0.08);
  color: var(--color-ink-black);
}

.page-title {
  flex: 1;
  font-size: 20px;
  color: var(--color-ink-black);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 8px 16px;
  border: 1px solid rgba(139, 115, 85, 0.2);
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--color-accent);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(139, 115, 85, 0.1);
}

.action-btn-danger {
  color: var(--color-error);
}

.action-btn-danger:hover {
  background: rgba(181, 71, 71, 0.1);
}

.filter-bar {
  display: flex;
  gap: 8px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(139, 115, 85, 0.1);
}

.filter-btn {
  padding: 6px 16px;
  border: none;
  background: transparent;
  border-radius: 20px;
  color: var(--color-ink-light);
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.filter-btn:hover {
  background: rgba(139, 115, 85, 0.08);
  color: var(--color-ink-black);
}

.filter-btn.active {
  background: rgba(139, 115, 85, 0.15);
  color: var(--color-accent);
  font-weight: 500;
}

.filter-badge {
  background: var(--color-error);
  color: white;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.notification-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

.notification-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px;
  background: white;
  border-radius: var(--radius-md);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid rgba(139, 115, 85, 0.08);
}

.notification-card:hover {
  border-color: rgba(139, 115, 85, 0.2);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.notification-card.unread {
  background: rgba(139, 115, 85, 0.03);
  border-color: rgba(139, 115, 85, 0.12);
}

.card-left {
  flex-shrink: 0;
}

.type-icon {
  font-size: 22px;
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.card-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-ink-black);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-time {
  font-size: 12px;
  color: var(--color-ink-faint);
  flex-shrink: 0;
  margin-left: 12px;
}

.card-content {
  font-size: 13px;
  color: var(--color-ink-light);
  margin: 0 0 8px 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
}

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.notification-card:hover .card-actions {
  opacity: 1;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(139, 115, 85, 0.06);
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-ink-light);
  font-size: 13px;
  transition: all 0.2s ease;
}

.icon-btn:hover {
  background: rgba(139, 115, 85, 0.15);
  color: var(--color-accent);
}

.icon-btn-delete:hover {
  background: rgba(181, 71, 71, 0.15);
  color: var(--color-error);
}

.empty-state {
  text-align: center;
  padding: 80px 40px;
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 16px;
  opacity: 0.4;
}

.empty-title {
  font-size: 16px;
  color: var(--color-ink-light);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 13px;
  color: var(--color-ink-faint);
}
</style>
