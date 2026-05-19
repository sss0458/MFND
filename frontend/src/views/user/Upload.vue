<template>
  <div class="zhixin-portal">
    <div class="cyber-background">
      <div class="glow-orb orb-1"></div>
      <div class="glow-orb orb-2"></div>
      <div class="grid-overlay"></div>
    </div>

    <header class="glass-header">
      <div class="brand-logo">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#00f2fe" stroke-width="2" stroke-linejoin="round"/>
          <path d="M2 17L12 22L22 17" stroke="#00f2fe" stroke-width="2" stroke-linejoin="round"/>
          <path d="M2 12L12 17L22 12" stroke="#4facfe" stroke-width="2" stroke-linejoin="round"/>
        </svg>
        <span class="brand-text">智信未来 <span class="light">ZhiXin AI</span></span>
      </div>
      <div class="user-actions">
        <el-tag effect="dark" color="rgba(16, 185, 129, 0.2)" style="border: 1px solid #10b981; color: #10b981; margin-right: 10px;">ENTERPRISE USER</el-tag>
        
        <div class="user-profile-trigger" @click="openProfileDialog">
          <el-icon class="user-icon"><User /></el-icon>
          <span class="username">{{ profileForm.nickname || authStore.username || 'User' }}</span>
        </div>

        <div class="logout-btn" @click="handleLogout" title="断开连接">
          <el-icon><SwitchButton /></el-icon>
        </div>
      </div>
    </header>

    <main class="portal-main">
      <div class="history-sidebar glass-panel">
        <button class="new-task-btn" @click="startNewTask">
          <el-icon><Plus /></el-icon> 新建检测任务
        </button>
        
        <div class="history-header">
          <span>历史请求 (MY REQUESTS)</span>
          <el-icon class="refresh-icon" @click="fetchHistory" :class="{'is-spinning': isFetchingHistory}"><Refresh /></el-icon>
        </div>

        <div class="history-list">
          <div 
            v-for="task in myTasks" :key="task.id"
            class="swipe-container"
            :class="{ 'show-delete': task.isSwiped }"
            @mousedown="startSwipe($event, task)"
            @mousemove="moveSwipe($event, task)"
            @mouseup="endSwipe"
            @mouseleave="endSwipe"
            @touchstart="startSwipe($event, task)"
            @touchmove="moveSwipe($event, task)"
            @touchend="endSwipe"
          >
            <div class="swipe-action" @click.stop="softDeleteTask(task)">
              <el-icon><Delete /></el-icon> 删除
            </div>

            <div 
              class="history-card"
              :class="{ active: currentTask?.id === task.id }"
              @click="viewHistoryTask(task)"
            >
              <div class="card-glow"></div>
              <div class="task-title">
                <span class="engine-tiny-tag" :class="task.title.includes('[PRO]') ? 'pro-tag' : 'fast-tag'">
                  {{ task.title.includes('[PRO]') ? 'PRO' : 'FAST' }}
                </span>
                {{ task.title.replace(/\[.*?\]\s*/, '') }}
              </div>
              <div class="task-meta">
                <span class="task-id">#{{ task.id.toString().slice(-6) }}</span>
                <span class="status-tag audited-tag" v-if="task.status === 'audited'"><el-icon><Check /></el-icon> 专家已审</span>
                <span class="status-tag pending-tag" v-else><el-icon><Loading /></el-icon> AI 初筛</span>
              </div>
            </div>
          </div>
          <div v-if="myTasks.length === 0" class="empty-history">暂无检测记录</div>
        </div>

        <div class="pagination-wrapper" v-if="totalTasks > 0">
          <el-pagination
            layout="prev, pager, next"
            :total="totalTasks"
            :page-size="pageSize"
            v-model:current-page="currentPage"
            @current-change="fetchHistory"
            small
            background
            class="cyber-pagination"
          />
        </div>
      </div>

      <div class="workspace-area">
        
        <div v-if="currentMode === 'NEW'" class="engine-container">
          <div class="input-nexus glass-panel">
            <div class="panel-title">01 / 数据注入 INPUT NEXUS</div>

            <div class="submit-mode-switch">
              <button class="mode-chip" :class="{ active: submissionMode === 'single' }" @click="submissionMode = 'single'">单条多模态</button>
              <button class="mode-chip" :class="{ active: submissionMode === 'batch' }" @click="submissionMode = 'batch'">批量新闻文本</button>
            </div>

            <template v-if="submissionMode === 'single'">
              <div class="input-group">
                <el-input v-model="postData.text" type="textarea" :rows="4" placeholder="输入需要检测的新闻正文、社交媒体推文..." class="cyber-textarea" />
              </div>

              <div class="media-grid">
                <el-upload action="#" list-type="picture-card" :auto-upload="false" :on-change="handleImageChange" :on-remove="handleImageRemove" multiple :limit="9" :file-list="imageList" class="cyber-uploader img-uploader">
                  <div class="upload-trigger"><el-icon><Picture /></el-icon><span>图像证据</span></div>
                </el-upload>

                <el-upload action="#" :auto-upload="false" :on-change="handleVideoChange" :on-remove="handleVideoRemove" :limit="1" :file-list="videoList" class="cyber-uploader vid-uploader">
                  <div class="upload-trigger">
                    <el-icon><VideoCamera /></el-icon>
                    <span v-if="videoList.length === 0">视频证据</span><span v-else class="success-text">已加载</span>
                  </div>
                </el-upload>
              </div>
            </template>

            <div v-else class="batch-panel">
              <div class="batch-tip">
                批量模式会将每条新闻逐条入库和检测。支持“一行一条”直接输入，或导入 `txt / csv / json` 文件；也支持同步上传多张图片，并按上传顺序与文本逐条对应。每条新闻最多配 1 张图，若图片少于文本，剩余文本会按纯文本检测。
              </div>
              <div class="input-group">
                <el-input
                  v-model="batchData.texts"
                  type="textarea"
                  :rows="8"
                  placeholder="每行一条新闻文本，例如：&#10;某平台出现伪造灾情图片并大量转发&#10;某明星深度合成视频正在传播"
                  class="cyber-textarea"
                />
              </div>
              <el-upload
                action="#"
                :auto-upload="false"
                :limit="1"
                accept=".txt,.csv,.json"
                :file-list="batchFileList"
                :on-change="handleBatchFileChange"
                :on-remove="handleBatchFileRemove"
                class="cyber-uploader batch-uploader"
              >
                <div class="upload-trigger">
                  <el-icon><Document /></el-icon>
                  <span v-if="batchFileList.length === 0">导入批量文件</span>
                  <span v-else class="success-text">{{ batchFileList[0].name }}</span>
                </div>
              </el-upload>
              <el-upload
                action="#"
                :auto-upload="false"
                multiple
                accept="image/*"
                :file-list="batchImageList"
                :on-change="handleBatchImageChange"
                :on-remove="handleBatchImageRemove"
                class="cyber-uploader batch-uploader batch-image-uploader"
              >
                <div class="upload-trigger">
                  <el-icon><Picture /></el-icon>
                  <span v-if="batchImageList.length === 0">导入批量图片</span>
                  <span v-else class="success-text">已选择 {{ batchImageList.length }} 张图片</span>
                </div>
              </el-upload>
            </div>

            <div class="engine-selector">
              <div class="selector-label">核心调度 // ENGINE ROUTING</div>
              <el-radio-group v-model="selectedEngine" class="cyber-radio-group">
                <el-radio-button label="fast" :disabled="!engineStatus.fast">
                  <span>FAST ⚡ (特征级融合对齐)</span>
                  <span v-if="!engineStatus.fast" class="offline-tag">[MAINTENANCE]</span>
                </el-radio-button>
                
                <el-radio-button label="pro" :disabled="!engineStatus.pro">
                  <span>PRO 🧠 (CMIE 语义逻辑推演)</span>
                  <span v-if="!engineStatus.pro" class="offline-tag">[OFFLINE]</span>
                </el-radio-button>
              </el-radio-group>
            </div>

            <button class="start-engine-btn" :class="{'is-loading': isAnalyzing}" @click="handleMultimodalSubmit">
              <span class="btn-text">
                <span v-if="isAnalyzing">正在连接 {{ selectedEngine.toUpperCase() }} 引擎...</span>
                <span v-else>{{ submissionMode === 'batch' ? `启动 ${selectedEngine.toUpperCase()} 批量检测` : `启动 ${selectedEngine.toUpperCase()} 融合分析` }}</span>
              </span>
              <div class="btn-glow"></div>
            </button>
          </div>

          <div class="output-nexus glass-panel">
            <div class="panel-title">02 / 智信终端 OUTPUT TERMINAL</div>
            <div v-if="!isAnalyzing" class="terminal-standby">
              <div class="pulse-ring"></div>
              <p>SYSTEM STANDBY</p>
              <span>等待数据注入以激活检测模型</span>
            </div>
            <div v-else class="terminal-analyzing">
              <div class="scanner-line"></div>
              <div class="data-stream" v-if="selectedEngine === 'fast'">
                <p>> 初始化 RoBERTa 语义提取器...</p>
                <p>> 载入 ViT 视觉 Transformer...</p>
                <p>> 建立高维特征对齐空间...</p>
              </div>
              <div class="data-stream pro-stream" v-else>
                <p>> 建立 MLLM 语义连接...</p>
                <p>> 提取视觉与文本实体锚点...</p>
                <p>> 构建图文共存关系 (CRG) 进行逻辑验证...</p>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="currentMode === 'RESULT' && resultData.isBatch" class="result-container glass-panel">
          <div class="panel-title">批量检测报告 // BATCH REPORT</div>

          <div class="batch-summary-grid">
            <div class="batch-summary-card">
              <span class="summary-label">总任务数</span>
              <strong>{{ resultData.batchSummary.total }}</strong>
            </div>
            <div class="batch-summary-card fake">
              <span class="summary-label">疑似伪造</span>
              <strong>{{ resultData.batchSummary.fakeCount }}</strong>
            </div>
            <div class="batch-summary-card real">
              <span class="summary-label">倾向真实</span>
              <strong>{{ resultData.batchSummary.realCount }}</strong>
            </div>
          </div>

          <div v-if="resultData.batchPreview.length > 0" class="batch-preview-panel">
            <div class="section-label">后端解析预览</div>
            <div class="batch-preview-tip">
              下面展示的是后端真正解析出的前几条样本，可用来确认 CSV / JSON / TXT 是否按预期进入模型。
            </div>
            <div class="batch-preview-list">
              <div v-for="(sample, index) in resultData.batchPreview" :key="`${index}-${sample}`" class="batch-preview-item">
                <span class="preview-index">#{{ index + 1 }}</span>
                <span class="preview-text">{{ sample }}</span>
              </div>
            </div>
          </div>

          <div class="batch-result-list">
            <div v-for="item in resultData.batchItems" :key="item.id || item.index" class="batch-result-card" :class="item.isFake ? 'fake' : 'real'">
              <div class="batch-result-head">
                <span>第 {{ item.index }} 条</span>
                <span>{{ item.isFake ? 'FAKE' : 'REAL' }} / {{ item.confidence.toFixed(2) }}%</span>
              </div>
              <div class="batch-result-meta">
                <span class="batch-media-tag" :class="item.hasImage ? 'with-image' : 'text-only'">
                  {{ item.hasImage ? '已绑定图片' : '纯文本' }}
                </span>
              </div>
              <div class="batch-result-text">{{ item.content }}</div>
              <div class="batch-result-reason">{{ item.features }}</div>
            </div>
          </div>
        </div>

        <div v-else-if="currentMode === 'RESULT'" class="result-container glass-panel">
          <div class="panel-title">智信诊断报告 // DIAGNOSTIC REPORT</div>
          
          <div class="report-grid">
            <div class="evidence-section">
              <div class="section-label">提交的证据载体</div>
              
              <div class="evidence-gallery" v-if="resultData.mediaUrls && resultData.mediaUrls.length > 0">
                <div v-for="(item, idx) in resultData.mediaUrls" :key="idx" class="gallery-item">
                  <video v-if="item.type==='video'" :src="item.url" controls />
                  <el-image v-else :src="item.url" fit="cover" :preview-src-list="[item.url]" />
                </div>
              </div>
              
              <div class="user-text-evidence" v-if="currentTask && currentTask.content">
                <div class="section-label" style="margin-top: 20px;">注入的文本数据</div>
                <div class="cyber-text-box">
                  {{ currentTask.content }}
                </div>
              </div>
              
              <div class="text-evidence" v-if="resultData.features">
                <div class="section-label" style="margin-top: 20px;">
                  <span v-if="resultData.modelUsed === 'pro'" class="pro-text-label">🧠 CMIE 大模型推演链条 (Insights)</span>
                  <span v-else>⚡ AI 特征提取过程</span>
                </div>
                <div class="evidence-box" :class="{ 'pro-box': resultData.modelUsed === 'pro' }">
                  <p style="white-space: pre-wrap;">{{ resultData.features }}</p>
                </div>
              </div>
            </div>

            <div class="verdict-section">
              
              <div v-if="resultData.status === 'audited'" class="human-audit-stamp">
                <div class="stamp-header">
                  <el-icon class="stamp-icon"><CircleCheckFilled v-if="resultData.auditResult==='REAL'"/><WarningFilled v-else/></el-icon>
                  <span>专家审计结果 // OFFICIAL VERDICT</span>
                </div>
                <div class="stamp-body" :class="resultData.auditResult === 'REAL' ? 'is-real' : 'is-fake'">
                  <h1 class="verdict-text">{{ resultData.auditResult === 'REAL' ? '未见明显伪造 (REAL)' : '确认为深度伪造 (FAKE)' }}</h1>
                  <p class="verdict-comment" v-if="resultData.auditComment">
                    <span class="auditor-note-label">审核员备注：</span>{{ resultData.auditComment }}
                  </p>
                </div>
              </div>

              <div v-else class="pending-audit-notice">
                <el-icon class="is-spinning"><Loading /></el-icon>
                <span>专家正在进行二次复核，请稍后刷新记录查看最终判决。</span>
              </div>

              <div class="verdict-box" :class="[resultData.isFake ? 'fake' : 'real', { 'is-overridden': resultData.status === 'audited' }]">
                <div class="ai-label">AI PREDICTION // 机器初筛 ({{ resultData.modelUsed === 'pro' ? 'CMIE PRO' : 'FAST ENGINE' }})</div>
                <h2 class="verdict-title">{{ resultData.isFake ? 'DETECTED: FAKE' : 'VERIFIED: REAL' }}</h2>
                <div class="confidence-bar">
                  <div class="bar-fill" :style="{width: resultData.confidence + '%'}"></div>
                </div>
                <div class="confidence-val">置信度: {{ resultData.confidence.toFixed(2) }}%</div>
              </div>

            </div>
          </div>

          <ReviewChat
            v-if="currentTask?.id"
            class="result-chat"
            :task-id="currentTask.id"
            role="user"
            :sender-name="profileForm.nickname || authStore.username || '用户'"
          />
        </div>

      </div>
    </main>

    <el-dialog 
      v-model="profileDialogVisible" 
      title="身份档案 // USER PROFILE" 
      width="420px" 
      class="cyber-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="profileForm" ref="profileFormRef" label-width="90px" class="cyber-form">
        <el-form-item label="账号ID">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>
        
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="profileForm.nickname" placeholder="输入您的显示昵称" />
        </el-form-item>
        
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="profileForm.email" placeholder="输入绑定的邮箱" />
        </el-form-item>
        
        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="profileForm.gender">
            <el-radio :label="0">保密</el-radio>
            <el-radio :label="1">男</el-radio>
            <el-radio :label="2">女</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="年龄" prop="age">
          <el-input-number v-model="profileForm.age" :min="1" :max="120" placeholder="年龄" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <button class="cyber-btn-cancel" @click="profileDialogVisible = false">取消同步</button>
          <button class="start-engine-btn save-btn" @click="submitProfile" :class="{'is-loading': isSavingProfile}">
            <span class="btn-text">{{ isSavingProfile ? 'UPLOADING...' : '确定' }}</span>
            <div class="btn-glow"></div>
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue' 
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { SwitchButton, Picture, VideoCamera, CircleCheckFilled, WarningFilled, Plus, Refresh, Check, Loading, User, Delete, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { uploadMedia, uploadBatchNews } from '@/api/task'
import ReviewChat from '@/components/ReviewChat.vue'
const api = axios.create({ baseURL: '/api' })

const authStore = useAuthStore()
const router = useRouter()

const currentMode = ref('NEW')
const submissionMode = ref('single')
const isAnalyzing = ref(false)
const isFetchingHistory = ref(false)
const selectedEngine = ref('fast') 
const totalTasks = ref(0)
const currentPage = ref(1)
const pageSize = ref(8)

const engineStatus = reactive({ fast: true, pro: true })

const fetchEngineStatus = async () => {
  try {
    const res = await api.get('/system/engine_status')
    if (res.data.code === 200) {
      engineStatus.fast = res.data.data.fast; engineStatus.pro = res.data.data.pro
    }
  } catch (error) { console.error('获取系统引擎状态失败，采用默认降级配置', error) }
}

watch(() => engineStatus.pro, (isProOnline) => {
  if (!isProOnline && selectedEngine.value === 'pro') {
    selectedEngine.value = 'fast'
    ElMessage.warning({ message: 'SYSTEM ALERT: Pro 引擎维护中，已为您自动降级至 Fast 引擎', customClass: 'cyber-toast' })
  }
})

const myTasks = ref([])
const currentTask = ref(null)

const profileDialogVisible = ref(false)
const isSavingProfile = ref(false)
const profileFormRef = ref(null)
const profileForm = reactive({ username: authStore.username || '', nickname: '', email: '', gender: 0, age: null })

const fetchUserProfile = async () => {
  if (!authStore.username) return
  try {
    const res = await api.get(`/user/profile?username=${authStore.username}`)
    if (res.data.code === 200) Object.assign(profileForm, res.data.data)
  } catch (error) { console.error('获取身份档案失败', error) }
}

const openProfileDialog = () => { profileDialogVisible.value = true }
const submitProfile = async () => {
  isSavingProfile.value = true
  try {
    const res = await api.put('/user/profile', profileForm)
    if (res.data.code === 200) { ElMessage.success({ message: 'DATA OVERWRITTEN / 核心数据已更新', customClass: 'cyber-toast' }); profileDialogVisible.value = false }
  } catch (error) { ElMessage.error({ message: '更新失败，请检查网络连接', customClass: 'cyber-toast' }) }
  finally { isSavingProfile.value = false }
}

const imageList = ref([])
const videoList = ref([])
const batchFileList = ref([])
const batchImageList = ref([])
const postData = reactive({ text: '', images: [], video: null })
const batchData = reactive({ texts: '', file: null, images: [] })
const resultData = reactive({
  isBatch: false,
  isFake: false,
  confidence: 0,
  features: '',
  mediaUrls: [],
  status: 'pending',
  auditResult: '',
  auditComment: '',
  modelUsed: 'fast',
  batchSummary: { total: 0, fakeCount: 0, realCount: 0 },
  batchPreview: [],
  batchItems: []
})

const isVideo = (url) => url && /\.(mp4|mov|avi|webm)$/i.test(url)

const resetResultData = () => {
  resultData.isBatch = false
  resultData.isFake = false
  resultData.confidence = 0
  resultData.features = ''
  resultData.mediaUrls = []
  resultData.status = 'pending'
  resultData.auditResult = ''
  resultData.auditComment = ''
  resultData.modelUsed = 'fast'
  resultData.batchSummary = { total: 0, fakeCount: 0, realCount: 0 }
  resultData.batchPreview = []
  resultData.batchItems = []
}

const fetchHistory = async () => {
  isFetchingHistory.value = true
  try {
    const res = await api.get(`/tasks?role=user&page=${currentPage.value}&size=${pageSize.value}`)
    if (res.data && res.data.code === 200) {
      myTasks.value = res.data.data.items.map(t => ({ ...t, isSwiped: false }))
      totalTasks.value = res.data.data.total
    } else if (Array.isArray(res.data)) {
      myTasks.value = res.data.map(t => ({ ...t, isSwiped: false }))
      totalTasks.value = res.data.length
    }
  } catch (e) { ElMessage.error('获取历史记录失败') } 
  finally { setTimeout(() => { isFetchingHistory.value = false }, 500) }
}

let startX = 0
let startY = 0
let swipeLocked = false
let pointerDown = false

const closeAllSwipes = (exceptId = null) => {
  myTasks.value.forEach((item) => {
    item.isSwiped = exceptId !== null && item.id === exceptId ? item.isSwiped : false
  })
}

const startSwipe = (e, task) => {
  const point = e.touches?.[0] || e
  startX = point?.clientX || 0
  startY = point?.clientY || 0
  swipeLocked = false
  pointerDown = true
}
const moveSwipe = (e, task) => {
  if (!startX || !pointerDown) return
  const point = e.touches?.[0] || e
  const currentX = point?.clientX || 0
  const currentY = point?.clientY || 0
  const deltaX = startX - currentX
  const deltaY = Math.abs(startY - currentY)

  if (swipeLocked) return
  if (Math.abs(deltaX) < 28) return
  if (Math.abs(deltaX) <= deltaY + 10) return

  swipeLocked = true
  if (deltaX > 0) {
    closeAllSwipes(task.id)
    task.isSwiped = true
  } else {
    task.isSwiped = false
  }
  startX = 0
  startY = 0
}
const endSwipe = () => {
  startX = 0
  startY = 0
  swipeLocked = false
  pointerDown = false
}

const softDeleteTask = async (task) => {
  try {
    await api.put(`/tasks/${task.id}/hide`)
    ElMessage.success({ message: '记录已清除', customClass: 'cyber-toast' })
    if (currentTask.value?.id === task.id) { startNewTask() }
    fetchHistory() 
  } catch (e) { ElMessage.error({ message: '清除失败', customClass: 'cyber-toast' }) }
}

onMounted(() => { fetchHistory(); fetchUserProfile(); fetchEngineStatus(); })

const startNewTask = () => {
  currentMode.value = 'NEW'
  currentTask.value = null
  submissionMode.value = 'single'
  postData.text = ''
  postData.images = []
  postData.video = null
  batchData.texts = ''
  batchData.file = null
  batchData.images = []
  imageList.value = []
  videoList.value = []
  batchFileList.value = []
  batchImageList.value = []
  resetResultData()
}

// 🛡️ 核心修复点：全面兼容数据库的下划线格式(snake_case)
const viewHistoryTask = (task) => {
  closeAllSwipes()
  currentMode.value = 'RESULT'
  currentTask.value = task
  
  // 兼容不同环境返回的键名差异
  const aiScore = task.ai_score !== undefined ? task.ai_score : task.aiScore;
  const aiReason = task.ai_reason || task.aiReason || '';
  const auditRes = task.audit_result || task.auditResult || '';
  const auditComm = task.audit_comment || task.auditComment || '';

  resultData.isFake = aiScore > 50
  resultData.confidence = aiScore > 50 ? aiScore : (100 - aiScore)
  resultData.features = aiReason
  resultData.status = task.status
  resultData.auditResult = auditRes
  resultData.auditComment = auditComm
  resultData.modelUsed = task.title && task.title.includes('[PRO]') ? 'pro' : 'fast'
  
  resultData.mediaUrls = []
  let parsedUrls = []
  try {
    if (task.media_urls) {
      parsedUrls = typeof task.media_urls === 'string' ? JSON.parse(task.media_urls) : task.media_urls
    }
    if (task.url && !parsedUrls.includes(task.url)) { parsedUrls.push(task.url) }
  } catch (e) { console.error("解析媒体数据失败", e) }

  if (Array.isArray(parsedUrls)) {
    parsedUrls.forEach(url => { resultData.mediaUrls.push({ type: isVideo(url) ? 'video' : 'image', url: url }) })
  }
}

const handleImageChange = (file, fileList) => { imageList.value = fileList; postData.images = fileList.map(f => f.raw) }
const handleImageRemove = (file, fileList) => { imageList.value = fileList; postData.images = fileList.map(f => f.raw) }
const handleVideoChange = (file) => { postData.video = file.raw; videoList.value = [file] }
const handleVideoRemove = () => { postData.video = null; videoList.value = [] }
const handleBatchFileChange = (file, fileList) => {
  batchFileList.value = fileList.slice(-1)
  batchData.file = batchFileList.value[0]?.raw || batchFileList.value[0] || null
}
const handleBatchFileRemove = () => {
  batchData.file = null
  batchFileList.value = []
}
const handleBatchImageChange = (file, fileList) => {
  batchImageList.value = fileList
  batchData.images = fileList.map((f) => f.raw).filter(Boolean)
}
const handleBatchImageRemove = (file, fileList) => {
  batchImageList.value = fileList
  batchData.images = fileList.map((f) => f.raw).filter(Boolean)
}

const countTextareaBatchTexts = (rawText) => {
  return (rawText || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .length
}

const countStructuredJsonItems = (rawText) => {
  const data = JSON.parse(rawText)
  const normalized = Array.isArray(data) ? data : (data?.items || data?.texts || data?.data || [])
  if (!Array.isArray(normalized)) return 0

  return normalized.reduce((count, item) => {
    if (typeof item === 'string' && item.trim()) return count + 1
    if (item && typeof item === 'object') return count + 1
    return count
  }, 0)
}

const countCsvRows = (rawText) => {
  const rows = (rawText || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  if (rows.length <= 1) return rows.length
  return rows.length - 1
}

const estimateBatchTextCount = async () => {
  let count = countTextareaBatchTexts(batchData.texts)

  if (!batchData.file) return count

  try {
    const fileName = batchData.file.name?.toLowerCase() || ''
    const fileText = await batchData.file.text()

    if (fileName.endsWith('.json')) {
      count += countStructuredJsonItems(fileText)
    } else if (fileName.endsWith('.csv')) {
      count += countCsvRows(fileText)
    } else {
      count += countTextareaBatchTexts(fileText)
    }
  } catch (error) {
    console.warn('批量文件条数预估失败，将交由后端进行最终校验', error)
  }

  return count
}

const handleSingleSubmit = async () => {
  if (!postData.text && postData.images.length === 0 && !postData.video) {
    return ElMessage.warning({ message: '智信系统提示：请投喂至少一种模态数据', customClass: 'cyber-toast' })
  }
  isAnalyzing.value = true

  try {
    const res = await uploadMedia({
      text: postData.text,
      images: postData.images,
      video: postData.video,
      modelType: selectedEngine.value
    })
    const delayTime = selectedEngine.value === 'pro' ? 2500 : 1500;
    
    setTimeout(async () => {
      const { isFake, confidence, features, modelUsed } = res.data
      resultData.isFake = isFake; resultData.confidence = confidence; resultData.features = features
      resultData.status = 'pending'; resultData.auditResult = ''; resultData.auditComment = ''
      resultData.modelUsed = modelUsed || selectedEngine.value 
      
      resultData.mediaUrls = []
      if (postData.images.length > 0) postData.images.forEach(img => resultData.mediaUrls.push({ type: 'image', url: URL.createObjectURL(img) }))
      if (postData.video) resultData.mediaUrls.push({ type: 'video', url: URL.createObjectURL(postData.video) })
      
      isAnalyzing.value = false
      currentMode.value = 'RESULT' 
      
      await fetchHistory()
      if (myTasks.value.length > 0) currentTask.value = myTasks.value[0]

    }, delayTime)
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '引擎连接失败')
    isAnalyzing.value = false
  }
}

const handleBatchSubmit = async () => {
  if (!batchData.texts.trim() && !batchData.file) {
    return ElMessage.warning({ message: '批量模式下请填写新闻文本，或上传 txt/csv/json 文件', customClass: 'cyber-toast' })
  }

  const estimatedTextCount = await estimateBatchTextCount()
  if (estimatedTextCount > 0 && batchData.images.length > estimatedTextCount) {
    return ElMessage.warning({ message: '批量图片数量不能多于文本条数，请按顺序一一对应上传', customClass: 'cyber-toast' })
  }
  if (estimatedTextCount > 0 && batchData.images.length > 0 && batchData.images.length < estimatedTextCount) {
    ElMessage.info({ message: '图片数量少于文本条数，剩余文本将按纯文本检测', customClass: 'cyber-toast' })
  }

  isAnalyzing.value = true

  try {
    const res = await uploadBatchNews({
      texts: batchData.texts,
      batchFile: batchData.file,
      images: batchData.images,
      modelType: selectedEngine.value
    })

    const { total, fakeCount, realCount, parsedPreview = [], items = [], modelUsed } = res.data
    resetResultData()
    resultData.isBatch = true
    resultData.modelUsed = modelUsed || selectedEngine.value
    resultData.batchSummary = { total, fakeCount, realCount }
    resultData.batchPreview = parsedPreview
    resultData.batchItems = items.map((item, index) => ({
      index: index + 1,
      id: item.taskId,
      title: item.title,
      content: item.content,
      isFake: item.isFake,
      confidence: item.confidence,
      features: item.features,
      hasImage: Array.isArray(item.mediaUrls) && item.mediaUrls.some((url) => !isVideo(url))
    }))

    currentTask.value = null
    currentMode.value = 'RESULT'
    await fetchHistory()
    ElMessage.success({ message: `批量检测完成，共处理 ${total} 条新闻`, customClass: 'cyber-toast' })
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '批量检测失败')
  } finally {
    isAnalyzing.value = false
  }
}

const handleMultimodalSubmit = async () => {
  if (submissionMode.value === 'batch') {
    await handleBatchSubmit()
    return
  }
  await handleSingleSubmit()
}

const handleLogout = () => { if (authStore.logout) authStore.logout(); router.push('/login') }
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;500;800&display=swap');

/* =========== 核心与背景 =========== */
.zhixin-portal { min-height: 100vh; background-color: #050505; color: #fff; font-family: 'Inter', sans-serif; position: relative; overflow: hidden; display: flex; flex-direction: column; }
.cyber-background { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
.glow-orb { position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.4; animation: float 10s infinite alternate ease-in-out; }
.orb-1 { width: 600px; height: 600px; background: #00f2fe; top: -200px; left: -100px; }
.orb-2 { width: 500px; height: 500px; background: #4facfe; bottom: -100px; right: -100px; animation-delay: -5s; }
.grid-overlay { position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px); background-size: 40px 40px; }
@keyframes float { 0% { transform: translate(0, 0); } 100% { transform: translate(50px, 50px); } }

/* =========== 导航栏 =========== */
.glass-header { position: relative; z-index: 10; display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; background: rgba(10, 10, 10, 0.6); backdrop-filter: blur(20px); border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
.brand-logo { display: flex; align-items: center; gap: 12px; }
.logo-icon { width: 28px; height: 28px; }
.brand-text { font-size: 18px; font-weight: 800; letter-spacing: 2px; }
.brand-text .light { font-weight: 300; color: #a0aec0; margin-left: 8px; font-size: 14px; }
.user-actions { display: flex; align-items: center; gap: 15px; }
.user-profile-trigger { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 8px; cursor: pointer; transition: 0.3s; background: rgba(255, 255, 255, 0.05); border: 1px solid transparent; }
.user-profile-trigger:hover { background: rgba(0, 242, 254, 0.1); border-color: rgba(0, 242, 254, 0.3); box-shadow: 0 0 10px rgba(0, 242, 254, 0.2); }
.user-icon { color: #00f2fe; font-size: 14px; }
.username { font-size: 13px; color: #e2e8f0; font-weight: 500; letter-spacing: 1px; }
.logout-btn { cursor: pointer; color: #fff; transition: 0.3s; opacity: 0.6; display: flex; align-items: center;}
.logout-btn:hover { opacity: 1; color: #f43f5e; transform: scale(1.1); }

/* =========== 布局与公用面板 =========== */
.portal-main { flex: 1; position: relative; z-index: 10; display: flex; gap: 20px; padding: 20px; overflow: hidden; max-width: 1600px; margin: 0 auto; width: 100%; box-sizing: border-box;}
.glass-panel { background: rgba(20, 20, 22, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; backdrop-filter: blur(30px); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); }
.panel-title { font-size: 12px; font-weight: 800; color: #00f2fe; margin-bottom: 20px; letter-spacing: 2px; }

/* =========== 左侧边栏 (历史记录) =========== */
.history-sidebar { width: 300px; display: flex; flex-direction: column; padding: 20px; flex-shrink: 0; }
.new-task-btn { width: 100%; padding: 12px; background: #00f2fe; color: #000; border: none; border-radius: 8px; font-weight: 800; font-size: 13px; cursor: pointer; transition: 0.3s; display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 25px; box-shadow: 0 5px 15px rgba(0,242,254,0.3); }
.new-task-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,242,254,0.5); }
.history-header { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #a0aec0; font-weight: bold; margin-bottom: 15px; }
.refresh-icon { cursor: pointer; transition: 0.3s; }
.refresh-icon:hover { color: #00f2fe; }
.is-spinning { animation: spin 1s linear infinite; }

.history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding-right: 5px; }
.history-list::-webkit-scrollbar { width: 4px; }
.history-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 2px; }

/* 👇 终极防重叠：采用纯粹的绝对定位处理滑块，完全隔离层级 */
.swipe-container { 
  position: relative; overflow: hidden; margin-bottom: 10px; border-radius: 10px; user-select: none; 
}
.history-card { 
  position: relative; z-index: 2; /* 在上方遮挡红色按钮 */
  background: #0f1115; /* 实心的深黑色背景 */
  width: 100%;
  box-sizing: border-box;
  padding: 15px; border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; 
  cursor: pointer; transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), border-color 0.3s;
}
.swipe-container:not(.show-delete) .history-card:hover { border-color: rgba(0,242,254,0.3); transform: translateX(5px); }
.history-card.active { border-color: #00f2fe; background: #0f1115; /* 激活时保持纯黑遮罩层 */ }

.swipe-action {
  position: absolute; top: 0; right: 0; width: 70px; height: 100%;
  background: linear-gradient(135deg, #f43f5e 0%, #be123c 100%); color: #fff;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  font-weight: 800; font-size: 11px; cursor: pointer; 
  z-index: 1; /* 躺在卡片的底层 */
  border-radius: 0 10px 10px 0; box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
}
.swipe-action:hover { filter: brightness(1.2); }

/* 滑动时，只有上层卡片向左滑，底部的红色按钮原地露出 */
.swipe-container.show-delete .history-card { transform: translateX(-70px); border-color: rgba(244,63,94,0.4); }

.card-glow { position: absolute; left: 0; top: 0; height: 100%; width: 3px; background: #00f2fe; opacity: 0; transition: 0.3s; }
.history-card.active .card-glow { opacity: 1; }
.engine-tiny-tag { font-size: 9px; padding: 1px 4px; border-radius: 3px; font-weight: bold; margin-right: 4px; border: 1px solid; }
.fast-tag { color: #00f2fe; border-color: rgba(0,242,254,0.5); background: rgba(0,242,254,0.1); }
.pro-tag { color: #a855f7; border-color: rgba(168,85,247,0.5); background: rgba(168,85,247,0.1); }
.task-title { font-size: 13px; font-weight: 500; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; }
.task-meta { display: flex; justify-content: space-between; align-items: center; font-size: 11px; }
.task-id { color: #718096; }
.status-tag { display: flex; align-items: center; gap: 4px; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;}
.audited-tag { color: #10b981; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); }
.pending-tag { color: #f59e0b; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }
.empty-history { text-align: center; color: #718096; font-size: 12px; margin-top: 20px; }

/* 分页器 */
.pagination-wrapper { display: flex; justify-content: center; margin-top: 15px; padding-top: 15px; border-top: 1px dashed rgba(255,255,255,0.1); }
.cyber-pagination { --el-pagination-bg-color: rgba(0,0,0,0.4); --el-pagination-text-color: #a0aec0; --el-pagination-hover-color: #00f2fe; }
.cyber-pagination :deep(.el-pager li) { border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; background: transparent; margin: 0 3px;}
.cyber-pagination :deep(.el-pager li.is-active) { background: rgba(0, 242, 254, 0.2); color: #00f2fe; border-color: #00f2fe; font-weight: 900; box-shadow: 0 0 10px rgba(0,242,254,0.3); }
.cyber-pagination :deep(button) { background: transparent !important; color: #718096 !important; }
.cyber-pagination :deep(button:disabled) { opacity: 0.3; }

/* =========== 右侧主工作区 =========== */
.workspace-area { flex: 1; overflow-y: auto; display: flex; flex-direction: column; }
.workspace-area::-webkit-scrollbar { width: 0; }
.engine-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; height: 100%; }
.input-nexus { padding: 30px; display: flex; flex-direction: column; }
.submit-mode-switch { display: flex; gap: 10px; margin-bottom: 16px; }
.mode-chip { flex: 1; border: 1px solid rgba(255,255,255,0.12); background: rgba(0,0,0,0.35); color: #a0aec0; border-radius: 10px; height: 42px; cursor: pointer; font-weight: 700; transition: 0.25s; }
.mode-chip.active { color: #00f2fe; border-color: rgba(0,242,254,0.55); box-shadow: 0 0 14px rgba(0,242,254,0.15); background: rgba(0,242,254,0.08); }
.cyber-textarea :deep(.el-textarea__inner) { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: #fff; border-radius: 12px; padding: 15px; font-size: 14px; transition: 0.3s; box-shadow: none; }
.cyber-textarea :deep(.el-textarea__inner:focus) { border-color: #00f2fe; background: rgba(0,242,254,0.05); }
.media-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 15px; margin: 20px 0; flex: 1; min-height: 0;}
.cyber-uploader :deep(.el-upload) { width: 100%; background: rgba(0,0,0,0.3); border: 1px dashed rgba(255,255,255,0.2); border-radius: 12px; transition: 0.3s; }
.cyber-uploader :deep(.el-upload:hover) { border-color: #00f2fe; background: rgba(0,242,254,0.05); }
.img-uploader :deep(.el-upload--picture-card) { height: 100px; }
.vid-uploader :deep(.el-upload) { height: 100px; display: flex; align-items: center; justify-content: center; }
.batch-panel { display: flex; flex-direction: column; gap: 16px; margin: 6px 0 20px; flex: 1; }
.batch-tip { font-size: 12px; color: #a0aec0; line-height: 1.7; padding: 12px 14px; border-radius: 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); }
.batch-uploader :deep(.el-upload) { min-height: 110px; display: flex; align-items: center; justify-content: center; }
.batch-image-uploader :deep(.el-upload) { min-height: 88px; }
.upload-trigger { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #a0aec0; font-size: 12px; }
.success-text { color: #10b981; }

.engine-selector { margin-bottom: 25px; }
.selector-label { font-size: 11px; color: #a0aec0; margin-bottom: 8px; font-weight: bold; letter-spacing: 1px;}
.cyber-radio-group { width: 100%; display: flex; }
.cyber-radio-group :deep(.el-radio-button) { flex: 1; }
.cyber-radio-group :deep(.el-radio-button__inner) { width: 100%; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1) !important; color: #718096; box-shadow: none !important; padding: 12px 0; font-weight: 800; transition: 0.3s; }
.cyber-radio-group :deep(.el-radio-button:first-child .el-radio-button__inner) { border-radius: 8px 0 0 8px; border-right: none !important; }
.cyber-radio-group :deep(.el-radio-button:last-child .el-radio-button__inner) { border-radius: 0 8px 8px 0; border-left: none !important;}
.cyber-radio-group :deep(.el-radio-button__original-radio[value="fast"]:checked + .el-radio-button__inner) { background: rgba(0, 242, 254, 0.1); color: #00f2fe; border-color: #00f2fe !important; box-shadow: 0 0 15px rgba(0,242,254,0.3) !important; }
.cyber-radio-group :deep(.el-radio-button__original-radio[value="pro"]:checked + .el-radio-button__inner) { background: rgba(168, 85, 247, 0.1); color: #a855f7; border-color: #a855f7 !important; box-shadow: 0 0 15px rgba(168,85,247,0.3) !important; }

.start-engine-btn { width: 100%; height: 50px; background: transparent; border: 1px solid #00f2fe; border-radius: 12px; color: #00f2fe; font-size: 14px; font-weight: 800; letter-spacing: 2px; cursor: pointer; position: relative; overflow: hidden; transition: 0.4s; flex-shrink: 0;}
.start-engine-btn:hover:not(.is-loading) { background: #00f2fe; color: #000; box-shadow: 0 0 20px rgba(0, 242, 254, 0.4); }
.btn-glow { position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent); transition: 0.5s; }
.start-engine-btn:hover .btn-glow { left: 100%; }
.is-loading { opacity: 0.7; cursor: not-allowed; border-color: #4facfe; color: #4facfe; }

.output-nexus { padding: 30px; display: flex; flex-direction: column; }
.terminal-standby { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #718096; opacity: 0.5; font-size: 13px;}
.pulse-ring { width: 40px; height: 40px; border: 2px solid #718096; border-radius: 50%; animation: pulse 2s infinite; margin-bottom: 20px; }
@keyframes pulse { 0% { transform: scale(0.8); opacity: 1; } 100% { transform: scale(1.5); opacity: 0; } }
.terminal-analyzing { flex: 1; position: relative; font-family: 'Courier New', monospace; color: #00f2fe; padding: 20px; background: rgba(0,0,0,0.4); border-radius: 12px; overflow: hidden; }
.scanner-line { position: absolute; top: 0; left: 0; width: 100%; height: 2px; background: #00f2fe; box-shadow: 0 0 10px #00f2fe; animation: scan 1.5s infinite linear; }
@keyframes scan { 0% { top: 0; } 100% { top: 100%; } }
.data-stream p { margin: 8px 0; font-size: 13px; opacity: 0; animation: type 0.5s forwards; }
.data-stream p:nth-child(2) { animation-delay: 0.5s; }
.data-stream p:nth-child(3) { animation-delay: 1s; }
.pro-stream p { color: #a855f7; }
@keyframes type { to { opacity: 1; } }

.offline-tag {color: #f43f5e; font-size: 10px; margin-left: 8px; font-weight: 900; letter-spacing: 1px; text-shadow: 0 0 5px rgba(244,63,94,0.5); animation: glitch 2s infinite;}
@keyframes glitch { 0% { opacity: 1; } 48% { opacity: 1; } 50% { opacity: 0.3; } 52% { opacity: 1; } 100% { opacity: 1; } }
.cyber-radio-group :deep(.el-radio-button.is-disabled .el-radio-button__inner) { background: rgba(0,0,0,0.8) !important; color: #4a5568 !important; border-color: rgba(255,255,255,0.05) !important; cursor: not-allowed; box-shadow: none !important; filter: grayscale(100%); }
.cyber-radio-group :deep(.el-radio-button.is-disabled.is-active .el-radio-button__inner) { background: rgba(244, 63, 94, 0.1) !important; color: #f43f5e !important; border-color: #f43f5e !important; }

/* =========== 诊断报告界面 =========== */
.result-container { padding: 30px; display: flex; flex-direction: column; min-height: 100%; box-sizing: border-box; }
.batch-summary-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 22px; }
.batch-summary-card { padding: 18px; border-radius: 14px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; gap: 10px; }
.batch-summary-card strong { font-size: 28px; color: #fff; }
.batch-summary-card.fake { border-color: rgba(244,63,94,0.35); background: rgba(244,63,94,0.08); }
.batch-summary-card.real { border-color: rgba(16,185,129,0.35); background: rgba(16,185,129,0.08); }
.summary-label { font-size: 12px; color: #a0aec0; }
.batch-preview-panel { margin-bottom: 20px; padding: 18px; border-radius: 14px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); }
.batch-preview-tip { font-size: 12px; color: #94a3b8; line-height: 1.6; margin-bottom: 12px; }
.batch-preview-list { display: grid; gap: 10px; }
.batch-preview-item { display: grid; grid-template-columns: 42px 1fr; gap: 12px; align-items: start; padding: 10px 12px; border-radius: 10px; background: rgba(0,0,0,0.28); border: 1px solid rgba(255,255,255,0.05); }
.preview-index { color: #00f2fe; font-size: 12px; font-weight: 800; }
.preview-text { color: #e2e8f0; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.batch-result-list { display: grid; gap: 14px; overflow-y: auto; padding-right: 4px; }
.batch-result-card { padding: 18px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08); background: rgba(8,12,16,0.82); }
.batch-result-card.fake { border-color: rgba(244,63,94,0.32); }
.batch-result-card.real { border-color: rgba(16,185,129,0.32); }
.batch-result-head { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 10px; font-size: 12px; color: #cbd5e1; font-weight: 700; }
.batch-result-meta { margin-bottom: 10px; }
.batch-media-tag { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; border: 1px solid rgba(255,255,255,0.12); }
.batch-media-tag.with-image { color: #38bdf8; background: rgba(56,189,248,0.08); border-color: rgba(56,189,248,0.28); }
.batch-media-tag.text-only { color: #94a3b8; background: rgba(148,163,184,0.08); border-color: rgba(148,163,184,0.2); }
.batch-result-text { color: #f8fafc; line-height: 1.7; margin-bottom: 12px; white-space: pre-wrap; }
.batch-result-reason { color: #94a3b8; line-height: 1.6; font-size: 13px; white-space: pre-wrap; }
.report-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; flex: 1; }
.result-chat { margin-top: 24px; min-height: 340px; }
.section-label { font-size: 12px; color: #a0aec0; margin-bottom: 15px; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 8px; }
.evidence-gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 15px; }
.gallery-item { border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); aspect-ratio: 1; background: #000;}
.gallery-item video, .gallery-item .el-image { width: 100%; height: 100%; object-fit: cover; }

/* 注入的文本框展示样式 */
.user-text-evidence { margin-top: 15px; }
.cyber-text-box { background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; font-size: 13px; line-height: 1.6; color: #e2e8f0; border: 1px solid rgba(255,255,255,0.05); word-break: break-all; }

.pro-text-label { color: #a855f7; font-weight: bold; }
.evidence-box { background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; border-left: 3px solid #00f2fe;}
.pro-box { border-left-color: #a855f7; background: rgba(168,85,247,0.05); }
.text-evidence p { font-size: 13px; line-height: 1.6; color: #e2e8f0; margin: 0; }

/* 结论章印与面板 */
.human-audit-stamp { margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1); padding: 20px; border-radius: 12px; background: linear-gradient(135deg, rgba(0,0,0,0.6) 0%, rgba(20,20,20,0.8) 100%); position: relative; overflow: hidden; animation: stampFade 0.5s ease-out; }
@keyframes stampFade { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
.stamp-header { display: flex; align-items: center; gap: 8px; font-size: 11px; color: #00f2fe; letter-spacing: 2px; margin-bottom: 15px; font-weight: bold; }
.stamp-body { padding: 15px; border-radius: 8px; border-left: 4px solid; background: rgba(0,0,0,0.4); }
.stamp-body.is-real { border-color: #10b981; }
.stamp-body.is-fake { border-color: #f43f5e; }
.verdict-text { font-size: 22px; font-weight: 900; margin: 0 0 10px 0; letter-spacing: 1px; }
.is-real .verdict-text { color: #10b981; }
.is-fake .verdict-text { color: #f43f5e; text-shadow: 0 0 15px rgba(244,63,94,0.3); }
.verdict-comment { font-size: 13px; color: #cbd5e1; margin: 0; line-height: 1.5; }
.auditor-note-label { color: #94a3b8; font-size: 11px; margin-right: 5px; }
.pending-audit-notice { display: flex; align-items: center; gap: 10px; background: rgba(245,158,11,0.1); border: 1px dashed rgba(245,158,11,0.4); color: #f59e0b; padding: 15px; border-radius: 12px; margin-bottom: 25px; font-size: 13px; }

.verdict-box { padding: 25px; border-radius: 12px; background: rgba(0,0,0,0.3); border-left: 4px solid; transition: 0.3s; }
.verdict-box.fake { border-color: #f43f5e; }
.verdict-box.real { border-color: #10b981; }
.verdict-box.is-overridden { opacity: 0.3; filter: grayscale(1); border-width: 2px; padding: 15px; }
.ai-label { font-size: 10px; color: #718096; margin-bottom: 8px; font-weight: bold; }
.verdict-title { font-size: 20px; font-weight: 800; letter-spacing: 1px; margin: 0 0 15px 0; }
.is-overridden .verdict-title { font-size: 16px; margin-bottom: 10px;}
.fake .verdict-title { color: #f43f5e; }
.real .verdict-title { color: #10b981; }
.confidence-bar { width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; margin-bottom: 8px; }
.bar-fill { height: 100%; transition: width 1s; }
.fake .bar-fill { background: #f43f5e; }
.real .bar-fill { background: #10b981; }
.confidence-val { font-size: 11px; color: #a0aec0; }

@media (max-width: 960px) {
  .engine-container,
  .report-grid,
  .batch-summary-grid { grid-template-columns: 1fr; }
  .media-grid { grid-template-columns: 1fr; }
}

:global(.cyber-toast) { background: rgba(10, 15, 20, 0.9) !important; border: 1px solid #00f2fe !important; backdrop-filter: blur(10px) !important; color: #fff !important; font-family: 'Inter', monospace !important; border-radius: 8px !important; }

:deep(.el-dialog.cyber-dialog) { background: rgba(15, 15, 18, 0.85); border: 1px solid rgba(0, 242, 254, 0.3); backdrop-filter: blur(20px); border-radius: 16px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8); }
:deep(.el-dialog__title) { color: #00f2fe; font-weight: 800; letter-spacing: 2px; font-size: 14px; }
:deep(.el-dialog__headerbtn .el-dialog__close) { color: #a0aec0; }
:deep(.el-dialog__headerbtn:hover .el-dialog__close) { color: #f43f5e; }
:deep(.el-form-item__label) { color: #a0aec0; }
:deep(.el-input__wrapper), :deep(.el-input-number__increase), :deep(.el-input-number__decrease) { background: rgba(0, 0, 0, 0.4) !important; box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) !important; }
:deep(.el-input__inner) { color: #fff; }
:deep(.el-input.is-disabled .el-input__wrapper) { background: rgba(0, 0, 0, 0.6) !important; }
:deep(.el-input.is-disabled .el-input__inner) { color: #718096; }
:deep(.el-radio__label) { color: #cbd5e1; }
:deep(.el-radio.is-checked .el-radio__label) { color: #00f2fe; }

.dialog-footer { display: flex; gap: 15px; justify-content: flex-end; }
.cyber-btn-cancel { background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #cbd5e1; padding: 0 20px; border-radius: 8px; cursor: pointer; transition: 0.3s; }
.cyber-btn-cancel:hover { background: rgba(255,255,255,0.1); color: #fff; }
.save-btn { width: auto; padding: 0 25px; height: 38px; }

.engine-tiny-tag { font-size: 9px; padding: 1px 4px; border-radius: 3px; font-weight: bold; margin-right: 4px; border: 1px solid; }
.fast-tag { color: #00f2fe; border-color: rgba(0,242,254,0.5); background: rgba(0,242,254,0.1); }
.pro-tag { color: #a855f7; border-color: rgba(168,85,247,0.5); background: rgba(168,85,247,0.1); }
.task-title { font-size: 13px; font-weight: 500; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; }
.task-meta { display: flex; justify-content: space-between; align-items: center; font-size: 11px; }
.task-id { color: #718096; }
.status-tag { display: flex; align-items: center; gap: 4px; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;}
.audited-tag { color: #10b981; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); }
.pending-tag { color: #f59e0b; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }
.empty-history { text-align: center; color: #718096; font-size: 12px; margin-top: 20px; }

/* 分页器 */
.pagination-wrapper { display: flex; justify-content: center; margin-top: 15px; padding-top: 15px; border-top: 1px dashed rgba(255,255,255,0.1); }
.cyber-pagination { --el-pagination-bg-color: rgba(0,0,0,0.4); --el-pagination-text-color: #a0aec0; --el-pagination-hover-color: #00f2fe; }
.cyber-pagination :deep(.el-pager li) { border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; background: transparent; margin: 0 3px;}
.cyber-pagination :deep(.el-pager li.is-active) { background: rgba(0, 242, 254, 0.2); color: #00f2fe; border-color: #00f2fe; font-weight: 900; box-shadow: 0 0 10px rgba(0,242,254,0.3); }
.cyber-pagination :deep(button) { background: transparent !important; color: #718096 !important; }
.cyber-pagination :deep(button:disabled) { opacity: 0.3; }

/* =========== 右侧主工作区 =========== */
.workspace-area { flex: 1; overflow-y: auto; display: flex; flex-direction: column; }
.workspace-area::-webkit-scrollbar { width: 0; }
.engine-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; height: 100%; }
.input-nexus { padding: 30px; display: flex; flex-direction: column; }
.cyber-textarea :deep(.el-textarea__inner) { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: #fff; border-radius: 12px; padding: 15px; font-size: 14px; transition: 0.3s; box-shadow: none; }
.cyber-textarea :deep(.el-textarea__inner:focus) { border-color: #00f2fe; background: rgba(0,242,254,0.05); }
.media-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 15px; margin: 20px 0; flex: 1; min-height: 0;}
.cyber-uploader :deep(.el-upload) { width: 100%; background: rgba(0,0,0,0.3); border: 1px dashed rgba(255,255,255,0.2); border-radius: 12px; transition: 0.3s; }
.cyber-uploader :deep(.el-upload:hover) { border-color: #00f2fe; background: rgba(0,242,254,0.05); }
.img-uploader :deep(.el-upload--picture-card) { height: 100px; }
.vid-uploader :deep(.el-upload) { height: 100px; display: flex; align-items: center; justify-content: center; }
.upload-trigger { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #a0aec0; font-size: 12px; }

.engine-selector { margin-bottom: 25px; }
.selector-label { font-size: 11px; color: #a0aec0; margin-bottom: 8px; font-weight: bold; letter-spacing: 1px;}
.cyber-radio-group { width: 100%; display: flex; }
.cyber-radio-group :deep(.el-radio-button) { flex: 1; }
.cyber-radio-group :deep(.el-radio-button__inner) { width: 100%; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1) !important; color: #718096; box-shadow: none !important; padding: 12px 0; font-weight: 800; transition: 0.3s; }
.cyber-radio-group :deep(.el-radio-button:first-child .el-radio-button__inner) { border-radius: 8px 0 0 8px; border-right: none !important; }
.cyber-radio-group :deep(.el-radio-button:last-child .el-radio-button__inner) { border-radius: 0 8px 8px 0; border-left: none !important;}
.cyber-radio-group :deep(.el-radio-button__original-radio[value="fast"]:checked + .el-radio-button__inner) { background: rgba(0, 242, 254, 0.1); color: #00f2fe; border-color: #00f2fe !important; box-shadow: 0 0 15px rgba(0,242,254,0.3) !important; }
.cyber-radio-group :deep(.el-radio-button__original-radio[value="pro"]:checked + .el-radio-button__inner) { background: rgba(168, 85, 247, 0.1); color: #a855f7; border-color: #a855f7 !important; box-shadow: 0 0 15px rgba(168,85,247,0.3) !important; }

.start-engine-btn { width: 100%; height: 50px; background: transparent; border: 1px solid #00f2fe; border-radius: 12px; color: #00f2fe; font-size: 14px; font-weight: 800; letter-spacing: 2px; cursor: pointer; position: relative; overflow: hidden; transition: 0.4s; flex-shrink: 0;}
.start-engine-btn:hover:not(.is-loading) { background: #00f2fe; color: #000; box-shadow: 0 0 20px rgba(0, 242, 254, 0.4); }
.btn-glow { position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent); transition: 0.5s; }
.start-engine-btn:hover .btn-glow { left: 100%; }
.is-loading { opacity: 0.7; cursor: not-allowed; border-color: #4facfe; color: #4facfe; }

.output-nexus { padding: 30px; display: flex; flex-direction: column; }
.terminal-standby { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #718096; opacity: 0.5; font-size: 13px;}
.pulse-ring { width: 40px; height: 40px; border: 2px solid #718096; border-radius: 50%; animation: pulse 2s infinite; margin-bottom: 20px; }
@keyframes pulse { 0% { transform: scale(0.8); opacity: 1; } 100% { transform: scale(1.5); opacity: 0; } }
.terminal-analyzing { flex: 1; position: relative; font-family: 'Courier New', monospace; color: #00f2fe; padding: 20px; background: rgba(0,0,0,0.4); border-radius: 12px; overflow: hidden; }
.scanner-line { position: absolute; top: 0; left: 0; width: 100%; height: 2px; background: #00f2fe; box-shadow: 0 0 10px #00f2fe; animation: scan 1.5s infinite linear; }
@keyframes scan { 0% { top: 0; } 100% { top: 100%; } }
.data-stream p { margin: 8px 0; font-size: 13px; opacity: 0; animation: type 0.5s forwards; }
.data-stream p:nth-child(2) { animation-delay: 0.5s; }
.data-stream p:nth-child(3) { animation-delay: 1s; }
.pro-stream p { color: #a855f7; }
@keyframes type { to { opacity: 1; } }
.offline-tag {color: #f43f5e; font-size: 10px; margin-left: 8px; font-weight: 900; letter-spacing: 1px; text-shadow: 0 0 5px rgba(244,63,94,0.5); animation: glitch 2s infinite;}
@keyframes glitch { 0% { opacity: 1; } 48% { opacity: 1; } 50% { opacity: 0.3; } 52% { opacity: 1; } 100% { opacity: 1; } }
.cyber-radio-group :deep(.el-radio-button.is-disabled .el-radio-button__inner) { background: rgba(0,0,0,0.8) !important; color: #4a5568 !important; border-color: rgba(255,255,255,0.05) !important; cursor: not-allowed; box-shadow: none !important; filter: grayscale(100%); }
.cyber-radio-group :deep(.el-radio-button.is-disabled.is-active .el-radio-button__inner) { background: rgba(244, 63, 94, 0.1) !important; color: #f43f5e !important; border-color: #f43f5e !important; }

/* =========== 诊断报告界面 =========== */
.result-container { padding: 30px; display: flex; flex-direction: column; min-height: 100%; box-sizing: border-box; }
.report-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; flex: 1; }
.section-label { font-size: 12px; color: #a0aec0; margin-bottom: 15px; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 8px; }
.evidence-gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 15px; }
.gallery-item { border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); aspect-ratio: 1; background: #000;}
.gallery-item video, .gallery-item .el-image { width: 100%; height: 100%; object-fit: cover; }

.user-text-evidence { margin-top: 15px; }
.cyber-text-box { background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; font-size: 13px; line-height: 1.6; color: #e2e8f0; border: 1px solid rgba(255,255,255,0.05); word-break: break-all; }

.pro-text-label { color: #a855f7; font-weight: bold; }
.evidence-box { background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; border-left: 3px solid #00f2fe;}
.pro-box { border-left-color: #a855f7; background: rgba(168,85,247,0.05); }
.text-evidence p { font-size: 13px; line-height: 1.6; color: #e2e8f0; margin: 0; }

/* 结论章印与面板 */
.human-audit-stamp { margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1); padding: 20px; border-radius: 12px; background: linear-gradient(135deg, rgba(0,0,0,0.6) 0%, rgba(20,20,20,0.8) 100%); position: relative; overflow: hidden; animation: stampFade 0.5s ease-out; }
@keyframes stampFade { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
.stamp-header { display: flex; align-items: center; gap: 8px; font-size: 11px; color: #00f2fe; letter-spacing: 2px; margin-bottom: 15px; font-weight: bold; }
.stamp-body { padding: 15px; border-radius: 8px; border-left: 4px solid; background: rgba(0,0,0,0.4); }
.stamp-body.is-real { border-color: #10b981; }
.stamp-body.is-fake { border-color: #f43f5e; }
.verdict-text { font-size: 22px; font-weight: 900; margin: 0 0 10px 0; letter-spacing: 1px; }
.is-real .verdict-text { color: #10b981; }
.is-fake .verdict-text { color: #f43f5e; text-shadow: 0 0 15px rgba(244,63,94,0.3); }
.verdict-comment { font-size: 13px; color: #cbd5e1; margin: 0; line-height: 1.5; }
.auditor-note-label { color: #94a3b8; font-size: 11px; margin-right: 5px; }
.pending-audit-notice { display: flex; align-items: center; gap: 10px; background: rgba(245,158,11,0.1); border: 1px dashed rgba(245,158,11,0.4); color: #f59e0b; padding: 15px; border-radius: 12px; margin-bottom: 25px; font-size: 13px; }

.verdict-box { padding: 25px; border-radius: 12px; background: rgba(0,0,0,0.3); border-left: 4px solid; transition: 0.3s; }
.verdict-box.fake { border-color: #f43f5e; }
.verdict-box.real { border-color: #10b981; }
.verdict-box.is-overridden { opacity: 0.3; filter: grayscale(1); border-width: 2px; padding: 15px; }
.ai-label { font-size: 10px; color: #718096; margin-bottom: 8px; font-weight: bold; }
.verdict-title { font-size: 20px; font-weight: 800; letter-spacing: 1px; margin: 0 0 15px 0; }
.is-overridden .verdict-title { font-size: 16px; margin-bottom: 10px;}
.fake .verdict-title { color: #f43f5e; }
.real .verdict-title { color: #10b981; }
.confidence-bar { width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; margin-bottom: 8px; }
.bar-fill { height: 100%; transition: width 1s; }
.fake .bar-fill { background: #f43f5e; }
.real .bar-fill { background: #10b981; }
.confidence-val { font-size: 11px; color: #a0aec0; }

:global(.cyber-toast) { background: rgba(10, 15, 20, 0.9) !important; border: 1px solid #00f2fe !important; backdrop-filter: blur(10px) !important; color: #fff !important; font-family: 'Inter', monospace !important; border-radius: 8px !important; }
:deep(.el-dialog.cyber-dialog) { background: rgba(15, 15, 18, 0.85); border: 1px solid rgba(0, 242, 254, 0.3); backdrop-filter: blur(20px); border-radius: 16px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8); }
:deep(.el-dialog__title) { color: #00f2fe; font-weight: 800; letter-spacing: 2px; font-size: 14px; }
:deep(.el-dialog__headerbtn .el-dialog__close) { color: #a0aec0; }
:deep(.el-dialog__headerbtn:hover .el-dialog__close) { color: #f43f5e; }
:deep(.el-form-item__label) { color: #a0aec0; }
:deep(.el-input__wrapper), :deep(.el-input-number__increase), :deep(.el-input-number__decrease) { background: rgba(0, 0, 0, 0.4) !important; box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) !important; }
:deep(.el-input__inner) { color: #fff; }
:deep(.el-input.is-disabled .el-input__wrapper) { background: rgba(0, 0, 0, 0.6) !important; }
:deep(.el-input.is-disabled .el-input__inner) { color: #718096; }
:deep(.el-radio__label) { color: #cbd5e1; }
:deep(.el-radio.is-checked .el-radio__label) { color: #00f2fe; }
.dialog-footer { display: flex; gap: 15px; justify-content: flex-end; }
.cyber-btn-cancel { background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #cbd5e1; padding: 0 20px; border-radius: 8px; cursor: pointer; transition: 0.3s; }
.cyber-btn-cancel:hover { background: rgba(255,255,255,0.1); color: #fff; }
.save-btn { width: auto; padding: 0 25px; height: 38px; }
</style>
