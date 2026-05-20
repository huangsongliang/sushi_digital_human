<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <h1 class="auth-title">Sushi Digital Human</h1>
        <p class="auth-subtitle">智能问答助手</p>
      </div>

      <div class="auth-tabs">
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'login' }"
          @click="activeTab = 'login'"
        >
          登录
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'register' }"
          @click="activeTab = 'register'"
        >
          注册
        </button>
      </div>

      <div class="auth-form" v-if="activeTab === 'login'">
        <div class="login-methods">
          <button 
            class="method-btn email" 
            :class="{ active: loginMethod === 'email' }"
            @click="loginMethod = 'email'"
          >
            <span class="icon">📧</span>
            邮箱登录
          </button>
          <button 
            class="method-btn phone" 
            :class="{ active: loginMethod === 'phone' }"
            @click="loginMethod = 'phone'"
          >
            <span class="icon">📱</span>
            手机登录
          </button>
          <button 
            class="method-btn github" 
            :class="{ active: loginMethod === 'github' }"
            @click="handleGithubLogin"
          >
            <span class="icon">🐙</span>
            GitHub
          </button>
        </div>

        <form v-if="loginMethod === 'email'" @submit.prevent="handleEmailLogin" class="form">
          <div class="form-group">
            <label>邮箱</label>
            <input 
              v-model="email" 
              type="email" 
              placeholder="请输入邮箱"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input 
              v-model="password" 
              type="password" 
              placeholder="请输入密码"
              class="form-input"
            />
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '登录中...' : '登录' }}
          </button>
        </form>

        <form v-if="loginMethod === 'phone'" @submit.prevent="handlePhoneLogin" class="form">
          <div class="form-group">
            <label>手机号</label>
            <input 
              v-model="phone" 
              type="tel" 
              placeholder="请输入手机号"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>验证码</label>
            <div class="code-input-group">
              <input 
                v-model="smsCode" 
                type="text" 
                placeholder="请输入验证码"
                class="form-input code-input"
              />
              <button 
                type="button" 
                class="send-code-btn"
                :disabled="isSending || phone.length < 11"
                @click="sendSmsCode"
              >
                {{ smsCountdown > 0 ? `${smsCountdown}s` : '发送验证码' }}
              </button>
            </div>
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '登录中...' : '登录' }}
          </button>
        </form>

        

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
      </div>

      <div class="auth-form" v-if="activeTab === 'register'">
        <div class="register-methods">
          <button 
            class="method-btn email" 
            :class="{ active: registerMethod === 'email' }"
            @click="registerMethod = 'email'"
          >
            <span class="icon">📧</span>
            邮箱注册
          </button>
          <button 
            class="method-btn phone" 
            :class="{ active: registerMethod === 'phone' }"
            @click="registerMethod = 'phone'"
          >
            <span class="icon">📱</span>
            手机注册
          </button>
        </div>

        <form v-if="registerMethod === 'email'" @submit.prevent="handleEmailRegister" class="form">
          <div class="form-group">
            <label>用户名</label>
            <input 
              v-model="regUsername" 
              type="text" 
              placeholder="请输入用户名"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>邮箱</label>
            <input 
              v-model="regEmail" 
              type="email" 
              placeholder="请输入邮箱"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input 
              v-model="regPassword" 
              type="password" 
              placeholder="请输入密码（至少6位）"
              class="form-input"
            />
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '注册中...' : '注册' }}
          </button>
        </form>

        <form v-if="registerMethod === 'phone'" @submit.prevent="handlePhoneRegister" class="form">
          <div class="form-group">
            <label>手机号</label>
            <input 
              v-model="regPhone" 
              type="tel" 
              placeholder="请输入手机号"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>验证码</label>
            <div class="code-input-group">
              <input 
                v-model="regSmsCode" 
                type="text" 
                placeholder="请输入验证码"
                class="form-input code-input"
              />
              <button 
                type="button" 
                class="send-code-btn"
                :disabled="isRegSending || regPhone.length < 11"
                @click="sendRegSmsCode"
              >
                {{ regSmsCountdown > 0 ? `${regSmsCountdown}s` : '发送验证码' }}
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>设置密码（可选）</label>
            <input 
              v-model="regPhonePassword" 
              type="password" 
              placeholder="设置登录密码（至少6位）"
              class="form-input"
            />
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '注册中...' : '注册' }}
          </button>
        </form>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
      </div>

      <div class="auth-footer">
        <p>
          <a href="#" class="link">忘记密码？</a>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';
const authStore = useAuthStore();
const router = useRouter();
const activeTab = ref<'login' | 'register'>('login');
const loginMethod = ref<'email' | 'phone' | 'github'>('email');
const registerMethod = ref<'email' | 'phone'>('email');
const email = ref('');
const password = ref('');
const phone = ref('');
const smsCode = ref('');
const regUsername = ref('');
const regEmail = ref('');
const regPassword = ref('');
const regPhone = ref('');
const regSmsCode = ref('');
const regPhonePassword = ref('');
const isLoading = ref(false);
const isSending = ref(false);
const isRegSending = ref(false);
const smsCountdown = ref(0);
const regSmsCountdown = ref(0);
const errorMessage = ref('');
let countdownTimer: ReturnType<typeof setInterval> | null = null;
const handleEmailLogin = async () => {
 if (!email.value || !password.value) {
 errorMessage.value = '请填写邮箱和密码';
 return;
 }
 isLoading.value = true;
 errorMessage.value = '';
 try {
 await authStore.login(email.value, password.value);
 router.push('/');
 }
 catch (err) {
 errorMessage.value = err instanceof Error ? err.message : '登录失败';
 }
 finally {
 isLoading.value = false;
 }
};
const handleGithubLogin = () => {
 window.location.href = 'http://localhost:8000/api/auth/github/redirect';
};

const handlePhoneLogin = async () => {
 if (!phone.value || !smsCode.value) {
 errorMessage.value = '请填写手机号和验证码';
 return;
 }
 isLoading.value = true;
 errorMessage.value = '';
 try {
 await authStore.loginWithPhone(phone.value, smsCode.value);
 router.push('/');
 }
 catch (err) {
 errorMessage.value = err instanceof Error ? err.message : '登录失败';
 }
 finally {
 isLoading.value = false;
 }
};
const handleEmailRegister = async () => {
 if (!regUsername.value || !regEmail.value || !regPassword.value) {
 errorMessage.value = '请填写所有必填项';
 return;
 }
 if (regPassword.value.length < 6) {
 errorMessage.value = '密码至少需要6位';
 return;
 }
 isLoading.value = true;
 errorMessage.value = '';
 try {
 await authStore.register(regUsername.value, regEmail.value, regPassword.value);
 activeTab.value = 'login';
 regUsername.value = '';
 regEmail.value = '';
 regPassword.value = '';
 }
 catch (err) {
 errorMessage.value = err instanceof Error ? err.message : '注册失败';
 }
 finally {
 isLoading.value = false;
 }
};
const handlePhoneRegister = async () => {
 if (!regPhone.value || !regSmsCode.value) {
 errorMessage.value = '请填写手机号和验证码';
 return;
 }
 isLoading.value = true;
 errorMessage.value = '';
 try {
 await authStore.registerWithPhone(regPhone.value, regSmsCode.value, regPhonePassword.value || undefined);
 activeTab.value = 'login';
 regPhone.value = '';
 regSmsCode.value = '';
 regPhonePassword.value = '';
 }
 catch (err) {
 errorMessage.value = err instanceof Error ? err.message : '注册失败';
 }
 finally {
 isLoading.value = false;
 }
};
const sendSmsCode = async () => {
 if (!phone.value || phone.value.length < 11) {
 errorMessage.value = '请输入正确的手机号';
 return;
 }
 isSending.value = true;
 try {
 await authStore.sendSmsCode(phone.value);
 smsCountdown.value = 60;
 countdownTimer = setInterval(() => {
 smsCountdown.value--;
 if (smsCountdown.value <= 0) {
 if (countdownTimer) {
 clearInterval(countdownTimer);
 countdownTimer = null;
 }
 }
 }, 1000);
 }
 catch (err) {
 errorMessage.value = err instanceof Error ? err.message : '发送验证码失败';
 }
 finally {
 isSending.value = false;
 }
};
const sendRegSmsCode = async () => {
 if (!regPhone.value || regPhone.value.length < 11) {
 errorMessage.value = '请输入正确的手机号';
 return;
 }
 isRegSending.value = true;
 try {
 await authStore.sendSmsCode(regPhone.value);
 regSmsCountdown.value = 60;
 countdownTimer = setInterval(() => {
 regSmsCountdown.value--;
 if (regSmsCountdown.value <= 0) {
 if (countdownTimer) {
 clearInterval(countdownTimer);
 countdownTimer = null;
 }
 }
 }, 1000);
 }
 catch (err) {
 errorMessage.value = err instanceof Error ? err.message : '发送验证码失败';
 }
 finally {
 isRegSending.value = false;
 }
};
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
  max-width: 420px;
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

.login-methods, .register-methods {
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
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
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
  transition: opacity 0.3s;
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.wechat-login {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.qrcode-container {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 30px;
  text-align: center;
}

.qrcode-placeholder {
  width: 160px;
  height: 160px;
  background: #f5f5f5;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.qrcode-icon {
  font-size: 48px;
}

.qrcode-tip {
  margin-top: 16px;
  color: #999;
  font-size: 14px;
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
