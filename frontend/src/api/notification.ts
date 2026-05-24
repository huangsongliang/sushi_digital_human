import { get, post, put, del } from '@/utils/request'

export interface ServerNotification {
  id: string
  user_id: number
  title: string
  content: string
  type: NotificationTypeEnum
  metadata: Record<string, unknown> | null
  is_read: boolean
  created_at: string
}

export type NotificationTypeEnum =
  | 'info'
  | 'success'
  | 'warning'
  | 'error'
  | 'document_update'
  | 'system_alert'
  | 'chat_message'

export interface NotificationListResponse {
  user_id: number
  notifications: ServerNotification[]
  count: number
  total: number
}

export interface UnreadCountResponse {
  user_id: number
  unread_count: number
}

export const notificationApi = {
  /** 获取用户通知列表 */
  list: (userId: number, unreadOnly = false, limit = 50) =>
    get<NotificationListResponse>(
      `/api/notifications/user/${userId}?unread_only=${unreadOnly}&limit=${limit}`,
    ),

  /** 获取未读通知数量 */
  unreadCount: (userId: number) =>
    get<UnreadCountResponse>(`/api/notifications/user/${userId}/unread-count`),

  /** 发送通知（管理员用） */
  send: (data: {
    user_id: number
    title: string
    content: string
    notification_type?: NotificationTypeEnum
    metadata?: Record<string, unknown>
  }) => post<{ status: string; notification_id: string; message: string }>(
    '/api/notifications/send',
    data,
  ),

  /** 标记单条通知为已读 */
  markRead: (notificationId: string, userId: number) =>
    put<{ status: string; message: string }>(
      `/api/notifications/${notificationId}/read`,
      { user_id: userId },
    ),

  /** 标记全部通知为已读 */
  markAllRead: (userId: number) =>
    put<{ status: string; message: string; count: number }>(
      `/api/notifications/user/${userId}/read-all`,
    ),

  /** 删除单条通知 */
  delete: (notificationId: string, userId: number) =>
    del<{ status: string; message: string }>(
      `/api/notifications/${notificationId}?user_id=${userId}`,
    ),

  /** 清空所有通知 */
  clearAll: (userId: number) =>
    del<{ status: string; message: string }>(
      `/api/notifications/user/${userId}/clear`,
    ),
}
