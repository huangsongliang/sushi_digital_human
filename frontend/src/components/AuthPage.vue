<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <h1 class="auth-title">Sushi Digital Human</h1>
        <p class="auth-subtitle">智能问答助手</p>
      </div>

      <div class="auth-tabs">
        <button class="tab-btn" :class="{ active: activeTab === 'login' }" @click="switchTab('login')">
          登录
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'register' }" @click="switchTab('register')">
          注册
        </button>
      </div>

      <!-- ============ 登录 ============ -->
      <div class="auth-form" v-if="activeTab === 'login'">
        <div class="login-methods">
          <button
            class="method-btn email"
            :class="{ active: loginMethod === 'email' }"
            @click="loginMethod = 'email'"
          >
            <span class="icon">&#x1F4E7;</span>
            邮箱登录
          </button>
          <button
            class="method-btn phone"
            :class="{ active: loginMethod === 'phone' }"
            @click="loginMethod = 'phone'"
          >
            <span class="icon">&#x1F4F1;</span>
            手机登录
          </button>
          <button class="method-btn github" @click="handleGithubLogin">
            <span class="icon">&#x1F419;</span>
            GitHub
          </button>
        </div>

        <!-- 邮箱登录表单 -->
        <form v-if="loginMethod === 'email'" @submit.prevent="handleEmailLogin" class="form" novalidate>
          <div class="form-group" :class="{ error: loginErrors.email }">
            <label>邮箱</label>
            <input
              v-model="email"
              type="email"
              placeholder="请输入邮箱"
              class="form-input"
              @input="loginErrors.email = ''"
            />
            <span class="field-error" v-if="loginErrors.email">{{ loginErrors.email }}</span>
          </div>
          <div class="form-group" :class="{ error: loginErrors.password }">
            <label>密码</label>
            <div class="password-input-wrap">
              <input
                v-model="password"
                :type="showLoginPwd ? 'text' : 'password'"
                placeholder="请输入密码"
                class="form-input"
                @input="loginErrors.password = ''"
              />
              <button type="button" class="toggle-pwd" @click="showLoginPwd = !showLoginPwd" tabindex="-1">
                {{ showLoginPwd ? '&#x1F648;' : '&#x1F441;' }}
              </button>
            </div>
            <span class="field-error" v-if="loginErrors.password">{{ loginErrors.password }}</span>
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '登录中...' : '登录' }}
          </button>
        </form>

        <!-- 手机登录表单 -->
        <form v-if="loginMethod === 'phone'" @submit.prevent="handlePhoneLogin" class="form" novalidate>
          <div class="form-group" :class="{ error: loginErrors.phone }">
            <label>手机号</label>
            <input
              v-model="phone"
              type="tel"
              placeholder="请输入11位手机号"
              class="form-input"
              maxlength="11"
              @input="loginErrors.phone = ''"
            />
            <span class="field-error" v-if="loginErrors.phone">{{ loginErrors.phone }}</span>
          </div>
          <div class="form-group" :class="{ error: loginErrors.smsCode }">
            <label>验证码</label>
            <div class="code-input-group">
              <input
                v-model="smsCode"
                type="text"
                placeholder="请输入验证码"
                class="form-input code-input"
                maxlength="6"
                @input="loginErrors.smsCode = ''"
              />
              <button
                type="button"
                class="send-code-btn"
                :disabled="loginSmsSending || smsCountdown > 0"
                @click="sendSmsCode"
              >
                {{ smsCountdown > 0 ? `${smsCountdown}s` : '发送验证码' }}
              </button>
            </div>
            <span class="field-error" v-if="loginErrors.smsCode">{{ loginErrors.smsCode }}</span>
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '登录中...' : '登录' }}
          </button>
        </form>

        <div v-if="errorMessage" class="error-message" role="alert">
          {{ errorMessage }}
        </div>
      </div>

      <!-- ============ 注册 ============ -->
      <div class="auth-form" v-if="activeTab === 'register'">
        <div class="register-methods">
          <button
            class="method-btn email"
            :class="{ active: registerMethod === 'email' }"
            @click="registerMethod = 'email'"
          >
            <span class="icon">&#x1F4E7;</span>
            邮箱注册
          </button>
          <button
            class="method-btn phone"
            :class="{ active: registerMethod === 'phone' }"
            @click="registerMethod = 'phone'"
          >
            <span class="icon">&#x1F4F1;</span>
            手机注册
          </button>
        </div>

        <!-- 邮箱注册表单 -->
        <form v-if="registerMethod === 'email'" @submit.prevent="handleEmailRegister" class="form" novalidate>
          <div class="form-group" :class="{ error: regErrors.username }">
            <label>用户名</label>
            <input
              v-model="regUsername"
              type="text"
              placeholder="请输入用户名（3-50位）"
              class="form-input"
              @input="regErrors.username = ''"
            />
            <span class="field-error" v-if="regErrors.username">{{ regErrors.username }}</span>
          </div>
          <div class="form-group" :class="{ error: regErrors.email }">
            <label>邮箱</label>
            <input
              v-model="regEmail"
              type="email"
              placeholder="请输入邮箱"
              class="form-input"
              @input="regErrors.email = ''"
            />
            <span class="field-error" v-if="regErrors.email">{{ regErrors.email }}</span>
          </div>
          <div class="form-group" :class="{ error: regErrors.password }">
            <label>密码</label>
            <div class="password-input-wrap">
              <input
                v-model="regPassword"
                :type="showRegPwd ? 'text' : 'password'"
                placeholder="至少8位，含大小写字母、数字和特殊字符"
                class="form-input"
                @input="onRegPasswordInput"
              />
              <button type="button" class="toggle-pwd" @click="showRegPwd = !showRegPwd" tabindex="-1">
                {{ showRegPwd ? '&#x1F648;' : '&#x1F441;' }}
              </button>
            </div>
            <!-- 密码强度条 -->
            <div class="password-strength" v-if="regPassword">
              <div class="strength-bar">
                <div class="strength-fill" :class="passwordStrengthClass" :style="{ width: passwordStrengthPercent + '%' }"></div>
              </div>
              <span class="strength-label" :class="passwordStrengthClass">{{ passwordStrengthLabel }}</span>
            </div>
            <span class="field-error" v-if="regErrors.password">{{ regErrors.password }}</span>
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '注册中...' : '注册' }}
          </button>
        </form>

        <!-- 手机注册表单 -->
        <form v-if="registerMethod === 'phone'" @submit.prevent="handlePhoneRegister" class="form" novalidate>
          <div class="form-group" :class="{ error: regErrors.phone }">
            <label>手机号</label>
            <input
              v-model="regPhone"
              type="tel"
              placeholder="请输入11位手机号"
              class="form-input"
              maxlength="11"
              @input="regErrors.phone = ''"
            />
            <span class="field-error" v-if="regErrors.phone">{{ regErrors.phone }}</span>
          </div>
          <div class="form-group" :class="{ error: regErrors.smsCode }">
            <label>验证码</label>
            <div class="code-input-group">
              <input
                v-model="regSmsCode"
                type="text"
                placeholder="请输入验证码"
                class="form-input code-input"
                maxlength="6"
                @input="regErrors.smsCode = ''"
              />
              <button
                type="button"
                class="send-code-btn"
                :disabled="regSmsSending || regSmsCountdown > 0"
                @click="sendRegSmsCode"
              >
                {{ regSmsCountdown > 0 ? `${regSmsCountdown}s` : '发送验证码' }}
              </button>
            </div>
            <span class="field-error" v-if="regErrors.smsCode">{{ regErrors.smsCode }}</span>
          </div>
          <div class="form-group" :class="{ error: regErrors.phonePassword }">
            <label>设置密码（可选）</label>
            <div class="password-input-wrap">
              <input
                v-model="regPhonePassword"
                :type="showRegPhonePwd ? 'text' : 'password'"
                placeholder="至少8位，含大小写字母、数字和特殊字符"
                class="form-input"
                @input="onRegPhonePasswordInput"
              />
              <button type="button" class="toggle-pwd" @click="showRegPhonePwd = !showRegPhonePwd" tabindex="-1">
                {{ showRegPhonePwd ? '&#x1F648;' : '&#x1F441;' }}
              </button>
            </div>
            <!-- 手机注册密码强度 -->
            <div class="password-strength" v-if="regPhonePassword">
              <div class="strength-bar">
                <div class="strength-fill" :class="phonePasswordStrengthClass" :style="{ width: phonePasswordStrengthPercent + '%' }"></div>
              </div>
              <span class="strength-label" :class="phonePasswordStrengthClass">{{ phonePasswordStrengthLabel }}</span>
            </div>
            <span class="field-error" v-if="regErrors.phonePassword">{{ regErrors.phonePassword }}</span>
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '注册中...' : '注册' }}
          </button>
        </form>

        <!-- 成功消息 -->
        <div v-if="successMessage" class="success-message" role="status">
          {{ successMessage }}
        </div>

        <!-- 错误消息 -->
        <div v-if="errorMessage" class="error-message" role="alert">
          {{ errorMessage }}
        </div>
      </div>

      <div class="auth-footer">
        <p><a href="#" class="link">忘记密码？</a></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

defineOptions({ name: 'AuthPage' })

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const authStore = useAuthStore()
const router = useRouter()

// --- 基础状态 ---
const activeTab = ref<'login' | 'register'>('login')
const loginMethod = ref<'email' | 'phone'>('email')
const registerMethod = ref<'email' | 'phone'>('email')
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

// --- 登录表单 ---
const email = ref('')
const password = ref('')
const phone = ref('')
const smsCode = ref('')
const showLoginPwd = ref(false)

const loginErrors = ref<Record<string, string>>({})

// 登录短信倒计时（独立 timer）
const smsCountdown = ref(0)
const loginSmsSending = ref(false)
let loginSmsTimer: ReturnType<typeof setInterval> | null = null

// --- 注册表单 ---
const regUsername = ref('')
const regEmail = ref('')
const regPassword = ref('')
const regPhone = ref('')
const regSmsCode = ref('')
const regPhonePassword = ref('')
const showRegPwd = ref(false)
const showRegPhonePwd = ref(false)

const regErrors = ref<Record<string, string>>({})

// 注册短信倒计时（独立 timer）
const regSmsCountdown = ref(0)
const regSmsSending = ref(false)
let regSmsTimer: ReturnType<typeof setInterval> | null = null

// --- 校验规则 ---

function isValidEmail(val: string): boolean {
  return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(val)
}

function isValidChinesePhone(val: string): boolean {
  return /^1[3-9]\d{9}$/.test(val)
}

interface PasswordCheck {
  valid: boolean
  percent: number
  cls: string
  label: string
}

function checkPasswordStrength(val: string): PasswordCheck {
  let score = 0
  if (val.length >= 8) score++
  if (val.length >= 12) score++
  if (/[a-z]/.test(val)) score++
  if (/[A-Z]/.test(val)) score++
  if (/[0-9]/.test(val)) score++
  if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(val)) score += 2
  // 最多 7 分
  const percent = Math.min(100, Math.round((score / 7) * 100))
  let cls: string
  let label: string
  if (score <= 2) {
    cls = 'weak'
    label = '弱'
  } else if (score <= 4) {
    cls = 'medium'
    label = '中等'
  } else {
    cls = 'strong'
    label = '强'
  }
  return { valid: score >= 5, percent, cls, label }
}

const passwordStrength = computed(() => checkPasswordStrength(regPassword.value))
const passwordStrengthPercent = computed(() => passwordStrength.value.percent)
const passwordStrengthClass = computed(() => passwordStrength.value.cls)
const passwordStrengthLabel = computed(() => passwordStrength.value.label)

const phonePasswordStrength = computed(() => checkPasswordStrength(regPhonePassword.value))
const phonePasswordStrengthPercent = computed(() => phonePasswordStrength.value.percent)
const phonePasswordStrengthClass = computed(() => phonePasswordStrength.value.cls)
const phonePasswordStrengthLabel = computed(() => phonePasswordStrength.value.label)

// --- 清空错误 ---
function clearAllErrors() {
  errorMessage.value = ''
  successMessage.value = ''
  loginErrors.value = {}
  regErrors.value = {}
}

function switchTab(tab: 'login' | 'register') {
  activeTab.value = tab
  clearAllErrors()
}

function onRegPasswordInput() {
  regErrors.value.password = ''
  // 实时提示但只在失焦或提交时展示
}

function onRegPhonePasswordInput() {
  regErrors.value.phonePassword = ''
}

// --- 开始/停止倒计时 ---
function startCountdown(current: ReturnType<typeof ref<number>>, timerRef: typeof loginSmsTimer) {
  current.value = 60
  if (timerRef) clearInterval(timerRef)
  // eslint-disable-next-line no-param-reassign
  timerRef = setInterval(() => {
    current.value--
    if (current.value <= 0) {
      if (timerRef) clearInterval(timerRef)
      // eslint-disable-next-line no-param-reassign
      timerRef = null
    }
  }, 1000)
}

// --- 邮箱登录 ---
async function handleEmailLogin() {
  clearAllErrors()
  let valid = true
  if (!email.value.trim()) {
    loginErrors.value.email = '请输入邮箱'
    valid = false
  } else if (!isValidEmail(email.value.trim())) {
    loginErrors.value.email = '邮箱格式不正确'
    valid = false
  }
  if (!password.value) {
    loginErrors.value.password = '请输入密码'
    valid = false
  }
  if (!valid) return

  isLoading.value = true
  try {
    await authStore.login(email.value.trim(), password.value)
    router.push('/')
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '登录失败'
  } finally {
    isLoading.value = false
  }
}

// --- 手机登录 ---
async function handlePhoneLogin() {
  clearAllErrors()
  let valid = true
  if (!phone.value.trim()) {
    loginErrors.value.phone = '请输入手机号'
    valid = false
  } else if (!isValidChinesePhone(phone.value.trim())) {
    loginErrors.value.phone = '请输入正确的11位手机号'
    valid = false
  }
  if (!smsCode.value.trim()) {
    loginErrors.value.smsCode = '请输入验证码'
    valid = false
  } else if (!/^\d{6}$/.test(smsCode.value.trim())) {
    loginErrors.value.smsCode = '验证码为6位数字'
    valid = false
  }
  if (!valid) return

  isLoading.value = true
  try {
    await authStore.loginWithPhone(phone.value.trim(), smsCode.value.trim())
    router.push('/')
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '登录失败'
  } finally {
    isLoading.value = false
  }
}

// --- 邮箱注册 ---
async function handleEmailRegister() {
  clearAllErrors()
  let valid = true
  if (!regUsername.value.trim()) {
    regErrors.value.username = '请输入用户名'
    valid = false
  } else if (regUsername.value.trim().length < 3) {
    regErrors.value.username = '用户名至少3位'
    valid = false
  }
  if (!regEmail.value.trim()) {
    regErrors.value.email = '请输入邮箱'
    valid = false
  } else if (!isValidEmail(regEmail.value.trim())) {
    regErrors.value.email = '邮箱格式不正确'
    valid = false
  }
  if (!regPassword.value) {
    regErrors.value.password = '请输入密码'
    valid = false
  } else if (!passwordStrength.value.valid) {
    regErrors.value.password = '密码至少8位，含大小写字母、数字和特殊字符'
    valid = false
  }
  if (!valid) return

  isLoading.value = true
  try {
    await authStore.register(regUsername.value.trim(), regEmail.value.trim(), regPassword.value)
    successMessage.value = `注册成功！3秒后自动切换到登录...`
    // 清空注册表单
    regUsername.value = ''
    regEmail.value = ''
    regPassword.value = ''
    // 自动切换
    setTimeout(() => {
      activeTab.value = 'login'
      successMessage.value = ''
      loginMethod.value = 'email'
    }, 3000)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '注册失败'
  } finally {
    isLoading.value = false
  }
}

// --- 手机注册 ---
async function handlePhoneRegister() {
  clearAllErrors()
  let valid = true
  if (!regPhone.value.trim()) {
    regErrors.value.phone = '请输入手机号'
    valid = false
  } else if (!isValidChinesePhone(regPhone.value.trim())) {
    regErrors.value.phone = '请输入正确的11位手机号'
    valid = false
  }
  if (!regSmsCode.value.trim()) {
    regErrors.value.smsCode = '请输入验证码'
    valid = false
  } else if (!/^\d{6}$/.test(regSmsCode.value.trim())) {
    regErrors.value.smsCode = '验证码为6位数字'
    valid = false
  }
  if (regPhonePassword.value && !phonePasswordStrength.value.valid) {
    regErrors.value.phonePassword = '密码至少8位，含大小写字母、数字和特殊字符'
    valid = false
  }
  if (!valid) return

  isLoading.value = true
  try {
    await authStore.registerWithPhone(
      regPhone.value.trim(),
      regSmsCode.value.trim(),
      regPhonePassword.value || undefined,
    )
    successMessage.value = `注册成功！3秒后自动切换到登录...`
    regPhone.value = ''
    regSmsCode.value = ''
    regPhonePassword.value = ''
    setTimeout(() => {
      activeTab.value = 'login'
      successMessage.value = ''
      loginMethod.value = 'phone'
    }, 3000)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '注册失败'
  } finally {
    isLoading.value = false
  }
}

// --- GitHub 登录 ---
function handleGithubLogin() {
  window.location.href = `${API_BASE}/api/auth/github/redirect`
}

// --- 发送短信验证码（登录） ---
async function sendSmsCode() {
  if (!phone.value.trim()) {
    loginErrors.value.phone = '请输入手机号'
    return
  }
  if (!isValidChinesePhone(phone.value.trim())) {
    loginErrors.value.phone = '请输入正确的11位手机号'
    return
  }
  loginSmsSending.value = true
  try {
    await authStore.sendSmsCode(phone.value.trim())
    smsCountdown.value = 60
    if (loginSmsTimer) clearInterval(loginSmsTimer)
    loginSmsTimer = setInterval(() => {
      smsCountdown.value--
      if (smsCountdown.value <= 0) {
        if (loginSmsTimer) {
          clearInterval(loginSmsTimer)
          loginSmsTimer = null
        }
      }
    }, 1000)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '发送验证码失败'
  } finally {
    loginSmsSending.value = false
  }
}

// --- 发送短信验证码（注册） ---
async function sendRegSmsCode() {
  if (!regPhone.value.trim()) {
    regErrors.value.phone = '请输入手机号'
    return
  }
  if (!isValidChinesePhone(regPhone.value.trim())) {
    regErrors.value.phone = '请输入正确的11位手机号'
    return
  }
  regSmsSending.value = true
  try {
    await authStore.sendSmsCode(regPhone.value.trim())
    regSmsCountdown.value = 60
    if (regSmsTimer) clearInterval(regSmsTimer)
    regSmsTimer = setInterval(() => {
      regSmsCountdown.value--
      if (regSmsCountdown.value <= 0) {
        if (regSmsTimer) {
          clearInterval(regSmsTimer)
          regSmsTimer = null
        }
      }
    }, 1000)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '发送验证码失败'
  } finally {
    regSmsSending.value = false
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.auth-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  padding: 40px;
  width: 100%;
  max-width: 440px;
  animation: fadeInUp 0.4s ease;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-header {
  text-align: center;
  margin-bottom: 30px;
}

.auth-title {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  margin: 0 0 8px 0;
}

.auth-subtitle {
  color: #999;
  font-size: 14px;
  margin: 0;
}

.auth-tabs {
  display: flex;
  margin-bottom: 24px;
  gap: 8px;
}

.tab-btn {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  background: #f5f5f5;
  color: #666;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.tab-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.login-methods,
.register-methods {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.method-btn {
  flex: 1;
  padding: 12px 8px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
  color: #666;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.method-btn .icon {
  font-size: 20px;
}

.method-btn.active {
  border-color: #667eea;
  background: #f0f0ff;
  color: #667eea;
}

.method-btn.github:hover {
  border-color: #333;
  background: #f9f9f9;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.form-input {
  padding: 12px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.3s;
  width: 100%;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

.form-group.error .form-input {
  border-color: #e53935;
}

/* 密码输入框 + 切换按钮 */
.password-input-wrap {
  position: relative;
  display: flex;
}

.password-input-wrap .form-input {
  padding-right: 44px;
}

.toggle-pwd {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 44px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  transition: color 0.2s;
}

.toggle-pwd:hover {
  color: #667eea;
}

.field-error {
  font-size: 12px;
  color: #e53935;
  min-height: 16px;
}

/* 密码强度指示器 */
.password-strength {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background: #eee;
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s, background 0.3s;
}

.strength-fill.weak {
  background: #e53935;
}

.strength-fill.medium {
  background: #fb8c00;
}

.strength-fill.strong {
  background: #43a047;
}

.strength-label {
  font-size: 12px;
  font-weight: 500;
  min-width: 30px;
  text-align: right;
}

.strength-label.weak {
  color: #e53935;
}

.strength-label.medium {
  color: #fb8c00;
}

.strength-label.strong {
  color: #43a047;
}

.code-input-group {
  display: flex;
  gap: 12px;
}

.code-input {
  flex: 1;
}

.send-code-btn {
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  background: #667eea;
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.3s;
  white-space: nowrap;
}

.send-code-btn:hover:not(:disabled) {
  background: #5a6fd6;
}

.send-code-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-btn {
  padding: 14px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.3s, transform 0.15s;
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.error-message {
  margin-top: 16px;
  padding: 12px;
  background: #ffebee;
  color: #c62828;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
}

.success-message {
  margin-top: 16px;
  padding: 12px;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
  animation: fadeInUp 0.3s ease;
}

.auth-footer {
  margin-top: 24px;
  text-align: center;
}

.link {
  color: #667eea;
  text-decoration: none;
  font-size: 14px;
}

.link:hover {
  text-decoration: underline;
}
</style>
