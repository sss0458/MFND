<template>
  <div class="zhixin-login-portal">
    <div class="cyber-background">
      <div class="glow-orb orb-primary"></div>
      <div class="glow-orb orb-secondary"></div>
      <div class="grid-overlay"></div>
    </div>

    <div class="login-wrapper">
      <div class="brand-header">
        <svg class="brand-logo" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M16 2L2 9L16 16L30 9L16 2Z" stroke="#00f2fe" stroke-width="1.5" stroke-linejoin="round" class="draw-anim-1"/>
          <path d="M2 23L16 30L30 23" stroke="#00f2fe" stroke-width="1.5" stroke-linejoin="round" class="draw-anim-2"/>
          <path d="M2 16L16 23L30 16" stroke="#4facfe" stroke-width="1.5" stroke-linejoin="round" class="draw-anim-3"/>
        </svg>
        <h1 class="brand-title">智信未来</h1>
        <p class="brand-subtitle">Multimodal Deepfake Detection Engine</p>
      </div>

      <div class="glass-login-panel">
        <div class="panel-decorator">
          <span class="dot"></span>
          <span class="line"></span>
          <span class="text">{{ isRegisterMode ? 'NEW NODE REGISTRATION // SYSTEM V2.0' : 'SECURE LOGIN & RECOVERY // SYSTEM V2.0' }}</span>
        </div>

        <el-form 
          ref="authFormRef"
          :model="authForm" 
          :rules="rules" 
          label-width="0px" 
          size="large"
          class="cyber-form"
        >
          <el-form-item prop="username">
            <el-input 
              v-model="authForm.username" 
              placeholder="ENTER SYSTEM ID"
              class="cyber-input"
            >
              <template #prefix>
                <el-icon class="input-icon"><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input 
              v-model="authForm.password" 
              type="password" 
              placeholder="ACCESS KEY"
              show-password
              class="cyber-input"
              @keyup.enter="handleAuth"
            >
              <template #prefix>
                <el-icon class="input-icon"><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="security_question" v-if="isRegisterMode">
            <el-input
              v-model="authForm.security_question"
              placeholder="SECURITY QUESTION"
              class="cyber-input"
            >
              <template #prefix>
                <el-icon class="input-icon"><ChatDotRound /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="security_answer" v-if="isRegisterMode">
            <el-input
              v-model="authForm.security_answer"
              placeholder="SECURITY ANSWER"
              class="cyber-input"
              @keyup.enter="handleAuth"
            >
              <template #prefix>
                <el-icon class="input-icon"><Key /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="captcha_code" v-if="isRegisterMode">
            <div class="captcha-row">
              <el-input 
                v-model="authForm.captcha_code" 
                placeholder="VERIFY CODE"
                class="cyber-input captcha-input"
                @keyup.enter="handleAuth"
              >
                <template #prefix>
                  <el-icon class="input-icon"><Key /></el-icon>
                </template>
              </el-input>
              <div class="captcha-img-box" @click="fetchCaptcha" title="REFRESH CODE">
                <img v-if="captchaImgBase64" :src="captchaImgBase64" alt="captcha" />
                <span v-else class="loading-text">LOADING...</span>
              </div>
            </div>
          </el-form-item>

          <el-form-item class="action-item">
            <button 
              type="button" 
              class="cyber-login-btn" 
              :class="{ 'is-loading': isLoading }"
              @click="handleAuth"
            >
              <span class="btn-text">
                {{ isLoading ? 'PROCESSING...' : (isRegisterMode ? 'INITIALIZE NEW NODE' : 'ESTABLISH CONNECTION') }}
              </span>
              <div class="btn-scanner"></div>
            </button>
          </el-form-item>
        </el-form>

        <div v-if="!isRegisterMode" class="secondary-actions">
          <span class="link-action" @click="openRecoveryDialog">>> FORGOT PASSWORD? VERIFY BY SECURITY QUESTION <<</span>
        </div>

        <div class="mode-toggle" @click="toggleMode">
          <span class="toggle-text">
            {{ isRegisterMode ? '>> RETURN TO LOGIN <<' : '>> REGISTER NEW NODE <<' }}
          </span>
        </div>

        <div class="footer-tips">
          <span class="tip-text">TEST ACC: admin / auditor / user</span>
        </div>
      </div>
    </div>
    
    <div class="corner-decoration top-right">VER: Z-F.2024.1</div>
    <div class="corner-decoration bottom-left">{{ isRegisterMode ? 'AWAITING REGISTRATION' : 'SECURE CONNECTION READY' }}</div>

    <el-dialog
      v-model="recoveryDialogVisible"
      width="480px"
      class="cyber-dialog"
      :teleported="false"
      destroy-on-close
      align-center
      @closed="resetRecoveryState"
    >
      <template #header>
        <div class="dialog-title">PASSWORD RECOVERY</div>
      </template>

      <el-form
        ref="recoveryFormRef"
        :model="recoveryForm"
        label-width="0"
        class="cyber-form recovery-form"
      >
        <el-form-item>
          <el-input
            v-model="recoveryForm.username"
            placeholder="ENTER SYSTEM ID"
            class="cyber-input"
            :disabled="recoveryStage === 2"
          >
            <template #prefix>
              <el-icon class="input-icon"><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="recoveryStage === 2">
          <el-input
            :model-value="recoveryQuestion"
            placeholder="SECURITY QUESTION"
            class="cyber-input"
            readonly
          >
            <template #prefix>
              <el-icon class="input-icon"><ChatDotRound /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="recoveryStage === 2">
          <el-input
            v-model="recoveryForm.security_answer"
            placeholder="YOUR ANSWER"
            class="cyber-input"
          >
            <template #prefix>
              <el-icon class="input-icon"><Key /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="recoveryStage === 2">
          <el-input
            v-model="recoveryForm.new_password"
            type="password"
            show-password
            placeholder="NEW ACCESS KEY"
            class="cyber-input"
            @keyup.enter="handleRecoveryReset"
          >
            <template #prefix>
              <el-icon class="input-icon"><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
      </el-form>

      <div class="dialog-actions">
        <button
          v-if="recoveryStage === 1"
          type="button"
          class="cyber-login-btn"
          :class="{ 'is-loading': recoveryLoading }"
          @click="handleFetchRecoveryQuestion"
        >
          <span class="btn-text">{{ recoveryLoading ? 'PROCESSING...' : 'LOAD SECURITY QUESTION' }}</span>
          <div class="btn-scanner"></div>
        </button>

        <button
          v-else
          type="button"
          class="cyber-login-btn"
          :class="{ 'is-loading': recoveryLoading }"
          @click="handleRecoveryReset"
        >
          <span class="btn-text">{{ recoveryLoading ? 'PROCESSING...' : 'RESET PASSWORD' }}</span>
          <div class="btn-scanner"></div>
        </button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { User, Lock, Key, ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  fetchRecoveryQuestionRequest,
  registerRequest,
  resetPasswordBySecurityRequest
} from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

const authFormRef = ref(null)
const isLoading = ref(false)
const isRegisterMode = ref(false) // 核心状态：是否为注册模式
const recoveryDialogVisible = ref(false)
const recoveryLoading = ref(false)
const recoveryStage = ref(1)
const recoveryQuestion = ref('')

// 验证码相关状态
const captchaId = ref('')
const captchaImgBase64 = ref('')

// 统一表单数据
const authForm = reactive({
  username: '',
  password: '',
  security_question: '',
  security_answer: '',
  captcha_code: ''
})

const recoveryFormRef = ref(null)
const recoveryForm = reactive({
  username: '',
  security_answer: '',
  new_password: ''
})

// 表单验证规则
const rules = reactive({
  username: [{ required: true, message: 'REQ: SYSTEM ID', trigger: 'blur' }],
  password: [{ required: true, message: 'REQ: ACCESS KEY', trigger: 'blur' }],
  security_question: [{ required: true, message: 'REQ: SECURITY QUESTION', trigger: 'blur' }],
  security_answer: [{ required: true, message: 'REQ: SECURITY ANSWER', trigger: 'blur' }],
  captcha_code: [{ required: true, message: 'REQ: VERIFY CODE', trigger: 'blur' }]
})

const resetRecoveryState = () => {
  recoveryStage.value = 1
  recoveryQuestion.value = ''
  recoveryForm.username = authForm.username || ''
  recoveryForm.security_answer = ''
  recoveryForm.new_password = ''
}

const openRecoveryDialog = () => {
  resetRecoveryState()
  recoveryDialogVisible.value = true
}

// 切换登录/注册模式
const toggleMode = () => {
  isRegisterMode.value = !isRegisterMode.value
  authFormRef.value?.resetFields()
  authForm.security_question = ''
  authForm.security_answer = ''
  authForm.captcha_code = ''
  if (isRegisterMode.value) {
    fetchCaptcha() // 进入注册模式时自动拉取验证码
  }
}

// 获取验证码
const fetchCaptcha = async () => {
  try {
    captchaImgBase64.value = '' // 清空显示加载中
    // 假设你在 vite.config.js 里配置了 /api 的 proxy
    const res = await fetch('/api/captcha')
    const result = await res.json()
    if (result.code === 200) {
      captchaId.value = result.data.captcha_id
      captchaImgBase64.value = result.data.image_base64
    }
  } catch (error) {
    ElMessage({ message: 'FAILED TO LOAD CAPTCHA', type: 'error', customClass: 'cyber-toast' })
  }
}

// 统一提交处理 (登录/注册)
const handleAuth = async () => {
  if (!authFormRef.value) return
  
  await authFormRef.value.validate(async (valid) => {
    if (valid) {
      isLoading.value = true
      try {
        if (isRegisterMode.value) {
          const res = await registerRequest({
            username: authForm.username,
            password: authForm.password,
            security_question: authForm.security_question,
            security_answer: authForm.security_answer,
            captcha_id: captchaId.value,
            captcha_code: authForm.captcha_code
          })

          const data = res.data
          if (data.code !== 200) {
            throw new Error(data.detail || data.message || 'REGISTRATION REJECTED')
          }

          ElMessage({ message: 'NODE INITIALIZED. PLEASE LOGIN.', type: 'success', customClass: 'cyber-toast' })
          toggleMode() // 注册成功后自动切回登录界面

        } else {
          // --- 登录逻辑 ---
          const role = await authStore.login(authForm) 
          ElMessage({ message: `ACCESS GRANTED: ${authForm.username}`, type: 'success', customClass: 'cyber-toast' })

          setTimeout(() => {
            switch (role) {
              case 'admin': router.push('/admin'); break;
              case 'auditor': router.push('/auditor'); break;
              default: router.push('/user');
            }
          }, 600)
        }
      } catch (error) {
        console.error(error)
        const errorMsg = error.message || error.response?.data?.detail || 'CONNECTION FAILED: CHECK CREDENTIALS'
        ElMessage({ message: errorMsg, type: 'error', customClass: 'cyber-toast' })
        
        // 如果是注册失败（比如验证码填错），自动刷新一下验证码
        if (isRegisterMode.value) {
          fetchCaptcha()
          authForm.captcha_code = '' // 清空输错的验证码
        }
      } finally {
        isLoading.value = false
      }
    }
  })
}

const handleFetchRecoveryQuestion = async () => {
  if (!recoveryForm.username.trim()) {
    ElMessage({ message: 'REQ: SYSTEM ID', type: 'warning', customClass: 'cyber-toast' })
    return
  }

  recoveryLoading.value = true
  try {
    const res = await fetchRecoveryQuestionRequest(recoveryForm.username.trim())
    recoveryQuestion.value = res.data?.data?.security_question || ''
    recoveryStage.value = 2
    ElMessage({ message: 'SECURITY QUESTION LOADED', type: 'success', customClass: 'cyber-toast' })
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || 'FAILED TO LOAD SECURITY QUESTION'
    ElMessage({ message: errorMsg, type: 'error', customClass: 'cyber-toast' })
  } finally {
    recoveryLoading.value = false
  }
}

const handleRecoveryReset = async () => {
  if (!recoveryForm.security_answer.trim() || !recoveryForm.new_password.trim()) {
    ElMessage({ message: 'REQ: ANSWER & NEW PASSWORD', type: 'warning', customClass: 'cyber-toast' })
    return
  }

  recoveryLoading.value = true
  try {
    const res = await resetPasswordBySecurityRequest({
      username: recoveryForm.username.trim(),
      security_answer: recoveryForm.security_answer,
      new_password: recoveryForm.new_password
    })

    if (res.data?.code !== 200) {
      throw new Error(res.data?.detail || res.data?.message || 'PASSWORD RESET FAILED')
    }

    authForm.username = recoveryForm.username.trim()
    authForm.password = ''
    recoveryDialogVisible.value = false
    resetRecoveryState()
    ElMessage({ message: 'PASSWORD RESET COMPLETE. PLEASE LOGIN.', type: 'success', customClass: 'cyber-toast' })
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || 'PASSWORD RESET FAILED'
    ElMessage({ message: errorMsg, type: 'error', customClass: 'cyber-toast' })
  } finally {
    recoveryLoading.value = false
  }
}
</script>

<style scoped>
/* 原有的引入和外层布局保持不变 */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&display=swap');

.zhixin-login-portal { min-height: 100vh; background-color: #030305; color: #fff; font-family: 'Inter', -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; position: relative; overflow: hidden; }
.cyber-background { position: absolute; inset: 0; pointer-events: none; z-index: 0; }
.glow-orb { position: absolute; border-radius: 50%; filter: blur(140px); opacity: 0.5; animation: floatOrb 15s infinite alternate ease-in-out; }
.orb-primary { width: 60vw; height: 60vw; background: #00f2fe; top: -30vw; right: -20vw; }
.orb-secondary { width: 50vw; height: 50vw; background: #4facfe; bottom: -20vw; left: -10vw; animation-delay: -5s; opacity: 0.3; }
.grid-overlay { position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px); background-size: 4vw 4vw; mask-image: radial-gradient(circle at center, black 40%, transparent 100%); -webkit-mask-image: radial-gradient(circle at center, black 40%, transparent 100%); }

@keyframes floatOrb { 0% { transform: translate(0, 0) scale(1); } 50% { transform: translate(-50px, 30px) scale(1.1); } 100% { transform: translate(30px, -50px) scale(0.9); } }

.login-wrapper { position: relative; z-index: 10; width: 100%; max-width: 440px; padding: 0 20px; display: flex; flex-direction: column; align-items: center; }
.brand-header { text-align: center; margin-bottom: 50px; }
.brand-logo { width: 60px; height: 60px; margin-bottom: 20px; }
.draw-anim-1 { stroke-dasharray: 100; stroke-dashoffset: 100; animation: draw 2s ease forwards; }
.draw-anim-2 { stroke-dasharray: 100; stroke-dashoffset: 100; animation: draw 2s ease forwards 0.3s; }
.draw-anim-3 { stroke-dasharray: 100; stroke-dashoffset: 100; animation: draw 2s ease forwards 0.6s; }
@keyframes draw { to { stroke-dashoffset: 0; } }

.brand-title { font-size: 36px; font-weight: 900; letter-spacing: 8px; margin: 0 0 10px 0; background: linear-gradient(to right, #fff, #a0aec0); -webkit-background-clip: text; background-clip: text; color: transparent; }
.brand-subtitle { font-size: 11px; font-weight: 300; letter-spacing: 3px; color: #718096; text-transform: uppercase; margin: 0; }

.glass-login-panel { width: 100%; background: rgba(10, 12, 16, 0.4); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px; padding: 40px; box-shadow: 0 30px 60px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.1); transform: translateY(0); transition: 0.5s cubic-bezier(0.25, 1, 0.5, 1); }
.glass-login-panel:hover { transform: translateY(-5px); box-shadow: 0 40px 80px rgba(0, 242, 254, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.15); border-color: rgba(0, 242, 254, 0.2); }

.panel-decorator { display: flex; align-items: center; gap: 10px; margin-bottom: 30px; opacity: 0.6; }
.panel-decorator .dot { width: 6px; height: 6px; background: #00f2fe; border-radius: 50%; box-shadow: 0 0 10px #00f2fe; animation: blink 2s infinite; }
.panel-decorator .line { height: 1px; flex: 1; background: linear-gradient(90deg, rgba(255,255,255,0.2), transparent); }
.panel-decorator .text { font-size: 10px; font-family: monospace; letter-spacing: 1px; color: #a0aec0; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.cyber-form { margin-bottom: 10px; }
.cyber-input :deep(.el-input__wrapper) { background-color: rgba(0, 0, 0, 0.4) !important; box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset !important; border-radius: 12px; padding: 4px 15px; transition: all 0.4s cubic-bezier(0.25, 1, 0.5, 1); }
.cyber-input :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px rgba(0, 242, 254, 0.4) inset !important; }
.cyber-input :deep(.el-input__wrapper.is-focus) { background-color: rgba(0, 242, 254, 0.05) !important; box-shadow: 0 0 0 1px #00f2fe inset, 0 0 20px rgba(0, 242, 254, 0.15) !important; }
.cyber-input :deep(.el-input__inner) { color: #fff !important; font-family: 'Inter', monospace; font-size: 13px; letter-spacing: 1px; height: 46px; }
.cyber-input :deep(.el-input__inner::placeholder) { color: #4a5568 !important; }
.input-icon { color: #a0aec0; font-size: 18px; transition: 0.3s; }
.cyber-input :deep(.el-input__wrapper.is-focus) .input-icon { color: #00f2fe; }

/* === 新增：验证码模块专属样式 === */
.captcha-row { display: flex; gap: 12px; width: 100%; align-items: center; }
.captcha-input { flex: 1; }
.captcha-img-box { width: 120px; height: 46px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); overflow: hidden; cursor: pointer; display: flex; justify-content: center; align-items: center; background: rgba(0, 0, 0, 0.6); transition: 0.3s; }
.captcha-img-box img { width: 100%; height: 100%; object-fit: cover; }
.loading-text { font-size: 10px; color: #4facfe; font-family: monospace; animation: blink 1s infinite; }
.captcha-img-box:hover { border-color: #00f2fe; box-shadow: 0 0 15px rgba(0, 242, 254, 0.2); }

.action-item { margin-top: 40px; margin-bottom: 0; }
.cyber-login-btn { width: 100%; height: 54px; background: transparent; border: 1px solid #00f2fe; border-radius: 12px; color: #00f2fe; font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 700; letter-spacing: 2px; cursor: pointer; position: relative; overflow: hidden; transition: all 0.4s cubic-bezier(0.25, 1, 0.5, 1); display: flex; align-items: center; justify-content: center; }
.cyber-login-btn:hover:not(.is-loading) { background: rgba(0, 242, 254, 0.1); box-shadow: 0 0 20px rgba(0, 242, 254, 0.3), inset 0 0 10px rgba(0, 242, 254, 0.2); text-shadow: 0 0 8px rgba(0, 242, 254, 0.8); }
.cyber-login-btn.is-loading { opacity: 0.6; cursor: not-allowed; border-color: #4facfe; color: #4facfe; }

.btn-scanner { position: absolute; top: 0; left: -100%; width: 50%; height: 100%; background: linear-gradient(90deg, transparent, rgba(0, 242, 254, 0.4), transparent); transform: skewX(-20deg); transition: 0s; }
.cyber-login-btn:hover .btn-scanner { animation: scan Sweep 1.5s infinite; }
@keyframes Sweep { 0% { left: -100%; } 100% { left: 200%; } }

/* === 新增：模式切换链接样式 === */
.secondary-actions { text-align: center; margin-top: 2px; }
.link-action { font-size: 11px; font-family: monospace; color: #7dd3fc; cursor: pointer; letter-spacing: 1px; transition: 0.3s; }
.link-action:hover { color: #00f2fe; text-shadow: 0 0 8px rgba(0,242,254,0.5); }
.mode-toggle { text-align: center; margin-top: 20px; font-size: 11px; font-family: monospace; color: #4facfe; cursor: pointer; letter-spacing: 1px; transition: 0.3s; }
.mode-toggle:hover { color: #00f2fe; text-shadow: 0 0 8px rgba(0,242,254,0.6); }

.footer-tips { text-align: center; margin-top: 20px; }
.tip-text { font-family: monospace; font-size: 10px; color: #4a5568; letter-spacing: 1px; }

.corner-decoration { position: absolute; font-family: monospace; font-size: 10px; color: #4a5568; letter-spacing: 2px; z-index: 0; }
.top-right { top: 30px; right: 40px; }
.bottom-left { bottom: 30px; left: 40px; }

:deep(.cyber-dialog) { border-radius: 18px; overflow: hidden; }
.dialog-title { color: #e6faff; font-family: 'Inter', monospace; letter-spacing: 2px; font-size: 14px; }
.recovery-form { margin-top: 8px; }
.dialog-actions { margin-top: 8px; }
:deep(.cyber-dialog.el-dialog) {
  background: linear-gradient(180deg, rgba(10, 14, 22, 0.98), rgba(4, 7, 12, 0.98)) !important;
  border: 1px solid rgba(0, 242, 254, 0.22) !important;
  border-radius: 18px !important;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
  backdrop-filter: blur(18px);
}
:deep(.cyber-dialog .el-dialog__header) {
  margin-right: 0;
  padding: 22px 22px 10px;
  background: transparent !important;
  border-bottom: 1px solid rgba(0, 242, 254, 0.1);
}
:deep(.cyber-dialog .el-dialog__body) {
  padding: 18px 22px 22px;
  background: transparent !important;
  color: #f8fafc !important;
}
:deep(.cyber-dialog .el-dialog__footer) {
  padding: 0 22px 22px;
  background: transparent !important;
}
:deep(.cyber-dialog .el-dialog__headerbtn .el-dialog__close) { color: #7dd3fc; }
:deep(.cyber-dialog .el-overlay-dialog) { display: flex; align-items: center; justify-content: center; }
:deep(.zhixin-login-portal > .el-overlay) { background: rgba(2, 6, 12, 0.62) !important; backdrop-filter: blur(6px); }
:deep(.cyber-dialog .el-form-item) { margin-bottom: 18px; }
:deep(.cyber-dialog .el-input__wrapper) {
  background: rgba(0, 0, 0, 0.72) !important;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset !important;
  border-radius: 12px !important;
}
:deep(.cyber-dialog .el-input__wrapper:hover) {
  background: rgba(0, 0, 0, 0.8) !important;
  box-shadow: 0 0 0 1px rgba(0, 242, 254, 0.35) inset !important;
}
:deep(.cyber-dialog .el-input__wrapper.is-focus) {
  background: rgba(0, 0, 0, 0.88) !important;
  box-shadow: 0 0 0 1px #00f2fe inset, 0 0 18px rgba(0, 242, 254, 0.16) !important;
}
:deep(.cyber-dialog .el-input__inner) {
  color: #f8fafc !important;
  background: transparent !important;
  -webkit-text-fill-color: #f8fafc !important;
  caret-color: #00f2fe !important;
}
:deep(.cyber-dialog .el-input__inner::placeholder) { color: #64748b !important; }
:deep(.cyber-dialog .el-input.is-disabled .el-input__wrapper) { background: rgba(8, 12, 18, 0.88) !important; }
:deep(.cyber-dialog input.el-input__inner:-webkit-autofill),
:deep(.cyber-dialog input.el-input__inner:-webkit-autofill:hover),
:deep(.cyber-dialog input.el-input__inner:-webkit-autofill:focus) {
  -webkit-text-fill-color: #f8fafc !important;
  transition: background-color 99999s ease-in-out 0s;
  box-shadow: 0 0 0 1000px rgba(0, 0, 0, 0.88) inset !important;
}

:global(.cyber-toast) { background: rgba(10, 15, 20, 0.9) !important; border: 1px solid #00f2fe !important; backdrop-filter: blur(10px) !important; color: #fff !important; font-family: 'Inter', monospace !important; border-radius: 8px !important; }
:global(.cyber-toast .el-message__content) { color: #fff !important; letter-spacing: 1px; }
</style>
