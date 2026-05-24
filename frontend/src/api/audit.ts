import { get, post } from '@/utils/request'

export interface AuditLogEntry {
  id: string
  action: string
  category: string
  user_id: string
  resource_type: string | null
  resource_id: string | null
  details: string | null
  ip_address: string | null
  user_agent: string | null
  status: string
  created_at: string
}

export interface AuditLogListResponse {
  logs: AuditLogEntry[]
  count: number
  limit: number
  offset: number
}

export interface AuditStatistics {
  actions: Record<string, number>
  categories: Record<string, number>
  top_users: Array<{ user_id: string; count: number }>
  total_count: number
  failed_count: number
}

export interface AuditStatisticsResponse {
  days: number
  start_time: string
  end_time: string
  statistics: AuditStatistics
}

export interface ActionType {
  value: string
  name: string
}

export interface CategoryType {
  value: string
  name: string
}

export const auditApi = {
  /** 查询审计日志 */
  queryLogs: (params: {
    user_id?: string
    action?: string
    category?: string
    resource_type?: string
    resource_id?: string
    start_time?: string
    end_time?: string
    status?: string
    limit?: number
    offset?: number
  }) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value))
      }
    })
    return get<AuditLogListResponse>(`/api/audit/logs?${searchParams.toString()}`)
  },

  /** 获取用户活动 */
  userActivity: (userId: string, days = 7, limit = 100) =>
    get<{ user_id: string; days: number; logs: AuditLogEntry[]; count: number }>(
      `/api/audit/user/${userId}/activity?days=${days}&limit=${limit}`,
    ),

  /** 获取失败操作 */
  failedAttempts: (hours = 24, limit = 100) =>
    get<{ hours: number; logs: AuditLogEntry[]; count: number }>(
      `/api/audit/security/failed-attempts?hours=${hours}&limit=${limit}`,
    ),

  /** 获取安全事件 */
  securityEvents: (days = 7, limit = 100) =>
    get<{ days: number; logs: AuditLogEntry[]; count: number }>(
      `/api/audit/security/events?days=${days}&limit=${limit}`,
    ),

  /** 获取统计 */
  statistics: (days = 7) =>
    get<AuditStatisticsResponse>(`/api/audit/statistics?days=${days}`),

  /** 导出日志 */
  exportLogs: (startTime: string, endTime: string) =>
    get<{ logs: AuditLogEntry[]; count: number }>(
      `/api/audit/export?start_time=${startTime}&end_time=${endTime}`,
    ),

  /** 清理旧日志 */
  cleanup: (days = 90) =>
    post<{ status: string; deleted_count: number; retained_days: number }>(
      `/api/audit/cleanup?days=${days}`,
    ),

  /** 获取操作类型 */
  actionTypes: () =>
    get<{ actions: ActionType[] }>('/api/audit/actions'),

  /** 获取类别类型 */
  categoryTypes: () =>
    get<{ categories: CategoryType[] }>('/api/audit/categories'),
}
