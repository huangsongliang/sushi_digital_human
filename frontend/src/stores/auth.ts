import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface User {
  id: number
  username: string
  email: string
  phone?: string
  roles: string[]
  permissions: string[]
}

export interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  isLoggedIn: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token') || null)
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token') || null)
  const user = ref<User | null>(null)
  const isLoggedIn = computed(() => !!accessToken.value)

  async function login(email: string, password: string): Promise<boolean> {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '登录失败')
      }

      const data = await response.json()
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token
      
      localStorage.setItem('access_token', data.access_token)
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }

      await fetchUser()
      return true
    } catch (error) {
      console.error('登录失败:', error)
      throw error
    }
  }

  async function loginWithPhone(phone: string, code: string): Promise<boolean> {
    try {
      const response = await fetch('/api/auth/login/phone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ phone, code })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '登录失败')
      }

      const data = await response.json()
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token
      
      localStorage.setItem('access_token', data.access_token)
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }

      await fetchUser()
      return true
    } catch (error) {
      console.error('手机号登录失败:', error)
      throw error
    }
  }

  async function register(username: string, email: string, password: string): Promise<boolean> {
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, email, password })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '注册失败')
      }

      return true
    } catch (error) {
      console.error('注册失败:', error)
      throw error
    }
  }

  async function registerWithPhone(phone: string, code: string, password?: string): Promise<boolean> {
    try {
      const response = await fetch('/api/auth/register/phone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ phone, code, password })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '注册失败')
      }

      return true
    } catch (error) {
      console.error('手机号注册失败:', error)
      throw error
    }
  }

  async function sendSmsCode(phone: string): Promise<boolean> {
    try {
      const response = await fetch('/api/auth/sms/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ phone })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '发送验证码失败')
      }

      return true
    } catch (error) {
      console.error('发送验证码失败:', error)
      throw error
    }
  }

  async function fetchUser(): Promise<void> {
    if (!accessToken.value) return

    try {
      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${accessToken.value}`
        }
      })

      if (response.ok) {
        user.value = await response.json()
      } else {
        logout()
      }
    } catch (error) {
      console.error('获取用户信息失败:', error)
      logout()
    }
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) return false

    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ refresh_token: refreshToken.value })
      })

      if (!response.ok) {
        logout()
        return false
      }

      const data = await response.json()
      accessToken.value = data.access_token
      localStorage.setItem('access_token', data.access_token)

      return true
    } catch (error) {
      console.error('刷新令牌失败:', error)
      logout()
      return false
    }
  }

  function logout(): void {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function getAuthHeader(): Record<string, string> {
    if (!accessToken.value) return {}
    return {
      'Authorization': `Bearer ${accessToken.value}`
    }
  }

  return {
    accessToken,
    refreshToken,
    user,
    isLoggedIn,
    login,
    loginWithPhone,
    register,
    registerWithPhone,
    sendSmsCode,
    fetchUser,
    refreshAccessToken,
    logout,
    getAuthHeader
  }
})
