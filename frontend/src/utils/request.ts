/**集中式 HTTP 客户端 — Token 自动刷新 + 请求拦截 + 响应处理 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

/**是否有正在进行的 Token 刷新请求（防并发） */
let isRefreshing = false
/**等待刷新的请求队列 */
const refreshQueue: Array<{
  resolve: (token: string) => void
  reject: (err: Error) => void
}> = []

function getAccessToken(): string | null {
  return localStorage.getItem('access_token')
}

function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token')
}

function setAuthTokens(access: string, refresh?: string) {
  localStorage.setItem('access_token', access)
  if (refresh) localStorage.setItem('refresh_token', refresh)
}

export function clearAuthTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

async function tryRefreshToken(): Promise<string> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    throw new Error('No refresh token')
  }

  const response = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!response.ok) {
    clearAuthTokens()
    throw new Error('Token refresh failed')
  }

  const data = await response.json()
  setAuthTokens(data.access_token)
  return data.access_token
}

async function handleTokenRefresh(): Promise<string> {
  // 如果正在刷新中，等待结果
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      refreshQueue.push({ resolve, reject })
    })
  }

  isRefreshing = true

  try {
    const newToken = await tryRefreshToken()
    // 通知等待队列
    refreshQueue.forEach(q => q.resolve(newToken))
    refreshQueue.length = 0
    return newToken
  } catch (err) {
    refreshQueue.forEach(q => q.reject(err instanceof Error ? err : new Error('Refresh failed')))
    refreshQueue.length = 0
    throw err
  } finally {
    isRefreshing = false
  }
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  skipAuth?: boolean
}

export async function request<T = unknown>(url: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth = false, body, headers: extraHeaders, ...rest } = options

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extraHeaders as Record<string, string>),
  }

  if (!skipAuth) {
    const token = getAccessToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
  }

  // 不自动加 Content-Type 的场景（FormData 等）
  if (body instanceof FormData) {
    delete headers['Content-Type']
  }

  const fetchOptions: RequestInit = {
    ...rest,
    headers,
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  }

  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`

  let response = await fetch(fullUrl, fetchOptions)

  // 401 自动刷新 Token 并重试一次
  if (response.status === 401 && !skipAuth && !url.includes('/api/auth/refresh') && !url.includes('/api/auth/login') && !url.includes('/api/auth/register')) {
    try {
      const newToken = await handleTokenRefresh()
      headers['Authorization'] = `Bearer ${newToken}`
      response = await fetch(fullUrl, {
        ...fetchOptions,
        headers,
      })
    } catch {
      // 刷新失败，清除认证状态
      clearAuthTokens()
      // 触发一个自定义事件，让 router 感知登出
      window.dispatchEvent(new CustomEvent('auth:logout'))
      throw new ApiError(401, '登录已过期，请重新登录')
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const detail = errorData.detail
    const message = typeof detail === 'string' ? detail : detail?.error || `请求失败 (${response.status})`
    throw new ApiError(response.status, message)
  }

  return response.json()
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**仅加 Authorization header 的 GET 请求 */
export async function get<T = unknown>(url: string, options?: RequestOptions): Promise<T> {
  return request<T>(url, { ...options, method: 'GET' })
}

export async function post<T = unknown>(url: string, body?: unknown, options?: RequestOptions): Promise<T> {
  return request<T>(url, { ...options, method: 'POST', body })
}
