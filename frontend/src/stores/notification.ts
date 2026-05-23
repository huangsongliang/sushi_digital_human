import { ref } from 'vue'
import { defineStore } from 'pinia'

export interface Notification {
  id: number
  title: string
  message: string
  type: 'success' | 'info' | 'warning' | 'error'
  duration?: number
}

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([])
  let nextId = 1

  function add(notification: Omit<Notification, 'id'>) {
    const id = nextId++
    const newNotification: Notification = {
      ...notification,
      id,
      duration: notification.duration || 4500
    }
    notifications.value.push(newNotification)

    const duration = newNotification.duration ?? 0
    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }
  }

  function remove(id: number) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  function success(title: string, message: string = '', duration?: number) {
    add({ title, message, type: 'success', duration })
  }

  function info(title: string, message: string = '', duration?: number) {
    add({ title, message, type: 'info', duration })
  }

  function warning(title: string, message: string = '', duration?: number) {
    add({ title, message, type: 'warning', duration })
  }

  function error(title: string, message: string = '', duration?: number) {
    add({ title, message, type: 'error', duration })
  }

  return { notifications, add, remove, success, info, warning, error }
})
