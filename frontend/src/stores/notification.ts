import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import { notificationApi, type ServerNotification, type NotificationTypeEnum } from '@/api/notification'

/** Toast 通知（浮动弹窗用） */
export interface ToastNotification {
  id: number
  title: string
  message: string
  type: 'success' | 'info' | 'warning' | 'error'
  duration?: number
}

export const useNotificationStore = defineStore('notification', () => {
  // ====== Toast 通知（右上角浮动弹窗） ======
  const toastNotifications = ref<ToastNotification[]>([])
  let nextId = 1

  // ====== 服务器持久化通知列表 ======
  const persistentNotifications = ref<ServerNotification[]>([])
  const loading = ref(false)
  const totalCount = ref(0)

  const unreadCount = computed(() =>
    persistentNotifications.value.filter(n => !n.is_read).length,
  )

  // ====== Toast 操作 ======
  function addToast(notification: Omit<ToastNotification, 'id'>) {
    const id = nextId++
    const newNotification: ToastNotification = {
      ...notification,
      id,
      duration: notification.duration || 4500,
    }
    toastNotifications.value.push(newNotification)

    const duration = newNotification.duration ?? 0
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }
  }

  function removeToast(id: number) {
    const index = toastNotifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      toastNotifications.value.splice(index, 1)
    }
  }

  function toastSuccess(title: string, message = '', duration?: number) {
    addToast({ title, message, type: 'success', duration })
  }

  function toastInfo(title: string, message = '', duration?: number) {
    addToast({ title, message, type: 'info', duration })
  }

  function toastWarning(title: string, message = '', duration?: number) {
    addToast({ title, message, type: 'warning', duration })
  }

  function toastError(title: string, message = '', duration?: number) {
    addToast({ title, message, type: 'error', duration })
  }

  // ====== 持久化通知操作 ======
  async function fetchNotifications(unreadOnly = false, limit = 50) {
    const authStore = useAuthStore()
    const userId = authStore.user?.id
    if (!userId) return

    loading.value = true
    try {
      const res = await notificationApi.list(userId, unreadOnly, limit)
      persistentNotifications.value = res.notifications
      totalCount.value = res.total
    } catch {
      // 静默失败，不影响页面
    } finally {
      loading.value = false
    }
  }

  async function fetchUnreadCount(): Promise<number> {
    const authStore = useAuthStore()
    const userId = authStore.user?.id
    if (!userId) return 0

    try {
      const res = await notificationApi.unreadCount(userId)
      return res.unread_count
    } catch {
      return 0
    }
  }

  async function markRead(notificationId: string) {
    const authStore = useAuthStore()
    const userId = authStore.user?.id
    if (!userId) return

    try {
      await notificationApi.markRead(notificationId, userId)
      const notification = persistentNotifications.value.find(n => n.id === notificationId)
      if (notification) {
        notification.is_read = true
      }
    } catch {
      // 静默失败
    }
  }

  async function markAllRead() {
    const authStore = useAuthStore()
    const userId = authStore.user?.id
    if (!userId) return

    try {
      await notificationApi.markAllRead(userId)
      persistentNotifications.value.forEach(n => {
        n.is_read = true
      })
    } catch {
      // 静默失败
    }
  }

  async function deleteNotification(notificationId: string) {
    const authStore = useAuthStore()
    const userId = authStore.user?.id
    if (!userId) return

    try {
      await notificationApi.delete(notificationId, userId)
      persistentNotifications.value = persistentNotifications.value.filter(
        n => n.id !== notificationId,
      )
      totalCount.value = Math.max(0, totalCount.value - 1)
    } catch {
      // 静默失败
    }
  }

  async function clearAll() {
    const authStore = useAuthStore()
    const userId = authStore.user?.id
    if (!userId) return

    try {
      await notificationApi.clearAll(userId)
      persistentNotifications.value = []
      totalCount.value = 0
    } catch {
      // 静默失败
    }
  }

  /** 发送通知（管理员用） */
  async function sendNotification(
    targetUserId: number,
    title: string,
    content: string,
    type: NotificationTypeEnum = 'info',
    metadata?: Record<string, unknown>,
  ) {
    try {
      await notificationApi.send({
        user_id: targetUserId,
        title,
        content,
        notification_type: type,
        metadata,
      })
    } catch {
      // 静默失败
    }
  }

  return {
    // Toast
    toastNotifications,
    addToast,
    removeToast,
    toastSuccess,
    toastInfo,
    toastWarning,
    toastError,
    // Persistent
    persistentNotifications,
    loading,
    totalCount,
    unreadCount,
    fetchNotifications,
    fetchUnreadCount,
    markRead,
    markAllRead,
    deleteNotification,
    clearAll,
    sendNotification,
  }
})
