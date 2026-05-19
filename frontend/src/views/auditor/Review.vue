<template>
  <div class="zhixin-auditor">
    <div class="nexus-background">
      <div class="grid-layer"></div>
    </div>

    <header class="glass-header">
      <div class="brand-logo">
        <span class="brand-text">智信未来 <span class="light">AUDITOR NEXUS</span></span>
      </div>
      <div class="user-actions">
        <el-tag effect="dark" color="rgba(0, 242, 254, 0.2)" style="border: 1px solid #00f2fe; color: #00f2fe">A.I. REVIEWER</el-tag>
        
        <div class="user-profile-trigger" @click="openProfileDialog">
          <el-icon class="user-icon"><User /></el-icon>
          <span class="username">{{ profileForm.nickname || authStore.username || 'Admin' }}</span>
        </div>

        <div class="logout-btn" @click="handleLogout" title="断开连接">
          <el-icon><SwitchButton /></el-icon>
        </div>
      </div>
    </header>

    <main class="auditor-main">
      <div class="task-sidebar glass-panel">
        <div class="sidebar-header">
          <div class="title-row">
            <span>数据流 MONITOR</span>
            <div class="sidebar-actions">
              <button class="download-btn" @click="downloadTaskData">批量下载</button>
              <el-badge :value="pendingCount" class="cyber-badge" />
            </div>
          </div>
          <div class="cyber-tabs">
            <div class="tab" :class="{active: filterType==='PENDING'}" @click="changeTab('PENDING')">待审核</div>
            <div class="tab" :class="{active: filterType==='AUDITED'}" @click="changeTab('AUDITED')">已归档</div>
          </div>
        </div>

        <div class="task-list">
          <div 
            v-for="item in allTasks" :key="item.id"
            class="cyber-task-card"
            :class="{ active: currentTask?.id === item.id }"
            @click="selectTask(item)"
          >
            <div class="card-glow"></div>
            <div class="task-id">#{{ item.id.toString().slice(-6) }}</div>
            
            <div class="task-title">
              <span class="engine-tiny-tag" :class="item.title.includes('[PRO]') ? 'pro-tag' : 'fast-tag'">
                {{ item.title.includes('[PRO]') ? 'PRO' : 'FAST' }}
              </span>
              {{ item.title.replace(/\[.*?\]\s*/, '') }}
            </div>

            <div class="task-meta">
              <div class="tags">
                <span class="cyber-tag" v-if="getMediaList(item).some(url => isVideo(url))">VIDEO</span>
                <span class="cyber-tag" v-if="getMediaList(item).some(url => !isVideo(url))">IMG</span>
                <span class="cyber-tag" v-if="item.content">TXT</span>
                
                <span class="cyber-tag xai-tag" v-if="getXaiList(item).length > 0">
                  XAI ({{ getXaiList(item).length }})
                </span>
                
                <span class="cyber-tag pro-mllm-tag" v-if="item.title.includes('[PRO]')">MLLM</span>
                
                <span class="cyber-tag" :class="(item.audit_result || item.auditResult) === 'FAKE' ? 'danger-tag' : 'safe-tag'" v-if="item.status === 'audited'">
                  {{ item.audit_result || item.auditResult }}
                </span>
              </div>
              
              <div class="score" :class="item.ai_score >= 50 ? 'danger' : 'safe'">
                {{ Number(item.ai_score || 0).toFixed(1) }}%
              </div>
            </div>
          </div>
          <div v-if="allTasks.length === 0" class="empty-history">当前队列无任务</div>
        </div>

        <div class="pagination-wrapper" v-if="totalTasks > 0">
          <el-pagination
            layout="prev, pager, next"
            :total="totalTasks"
            :page-size="pageSize"
            v-model:current-page="currentPage"
            @current-change="fetchTasks"
            small
            background
            class="cyber-pagination"
          />
        </div>
      </div>

      <div class="review-workspace">
        <template v-if="currentTask">
          <div class="workspace-grid">
            
            <div class="media-carousel-panel glass-panel">
              <div class="panel-label">EVIDENCE GALLERY // 多模态锚点分析</div>
              
              <div class="carousel-container" v-if="combinedMediaList.length > 0">
                <button class="nav-btn prev-btn" @click="prevMedia" :disabled="currentMediaIndex === 0">
                  <el-icon><ArrowLeft /></el-icon>
                </button>
                
                <div class="media-frame" :class="{ 'xai-frame': currentMediaItem.type === 'xai' }">
                  <div class="frame-corner xai-corner top-left"></div><div class="frame-corner xai-corner top-right"></div>
                  <div class="frame-corner xai-corner bottom-left"></div><div class="frame-corner xai-corner bottom-right"></div>
                  
                  <video 
                    v-if="currentMediaItem.isVideo" 
                    :src="currentMediaItem.url" 
                    controls 
                    class="media-content" 
                  />
                  <el-image 
                    v-else 
                    :src="currentMediaItem.url" 
                    fit="contain" 
                    class="media-content" 
                    :preview-src-list="[currentMediaItem.url]" 
                  />
                  
                  <div class="frame-label" :class="{ 'xai-label': currentMediaItem.type === 'xai' }">
                    {{ currentMediaItem.label }}
                    <span class="counter">[{{ currentMediaIndex + 1 }} / {{ combinedMediaList.length }}]</span>
                  </div>
                  <div class="scan-line" v-if="currentMediaItem.type === 'xai'"></div> 
                </div>

                <button class="nav-btn next-btn" @click="nextMedia" :disabled="currentMediaIndex === combinedMediaList.length - 1">
                  <el-icon><ArrowRight /></el-icon>
                </button>
              </div>
              <div v-else class="empty-media">PURE TEXT MODALITY DETECTED</div>
            </div>

            <div class="right-column">
              
              <div class="text-panel glass-panel">
                <div class="panel-label">SEMANTIC DATA // 语义层捕获</div>
                <div class="cyber-text-box">
                  {{ currentTask.content || 'NO TEXT DATA EXTRACTED.' }}
                </div>
              </div>

              <div class="decision-panel glass-panel">
                <div class="panel-label">HUMAN IN THE LOOP // 人工干预与对齐</div>
                
                <div class="ai-suggestion" :class="[currentTask.ai_score >= 50 ? 'alert' : 'pass',{ 'is-pro-suggestion': currentTask.title.includes('[PRO]') }]">
                  <div class="sugg-header">
                    <span v-if="currentTask.title.includes('[PRO]')">🧠 CMIE 大模型推演链条 (Insights):</span>
                    <span v-else>⚡ 系统判定特征空间:</span>
                  </div>
                  <div class="sugg-body" style="white-space: pre-wrap;">{{ currentTask.ai_reason }}</div>
                </div>

                <div class="decision-actions">
                  <div class="radio-cyber">
                    <label class="radio-label">
                      <input type="radio" v-model="auditForm.result" value="REAL" name="decision">
                      <span class="custom-radio real">标记为真实 (REAL)</span>
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="auditForm.result" value="FAKE" name="decision">
                      <span class="custom-radio fake">确认伪造 (FAKE)</span>
                    </label>
                  </div>

                  <input v-model="auditForm.comment" class="cyber-input" placeholder="输入纠偏反馈，用于模型负采样微调..." />
                  
                  <button 
                    class="submit-cyber-btn" 
                    :class="{ 'is-update': currentTask.status === 'audited' }"
                    @click="submitReview" 
                    :disabled="isLoading"
                  >
                    {{ isLoading ? 'UPDATING DB...' : (currentTask.status === 'audited' ? '⚠️ 修改历史裁决 (UPDATE DECISION)' : '提交裁决 (SYNC TO MODEL)') }}
                  </button>
                </div>
              </div>

              <ReviewChat
                class="auditor-chat"
                :task-id="currentTask.id"
                role="auditor"
                :sender-name="profileForm.nickname || authStore.username || '审核员'"
              />
            </div>
            </div>
        </template>

        <div v-else class="standby-screen glass-panel">
          <div class="standby-content">
            <div class="crosshair"></div>
            <p>AWAITING TASK SELECTION</p>
          </div>
        </div>
      </div>
    </main>

    <el-dialog 
      v-model="profileDialogVisible" 
      title="审查员档案 // REVIEWER PROFILE" 
      width="420px" 
      class="cyber-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="profileForm" ref="profileFormRef" label-width="90px" class="cyber-form">
        <el-form-item label="核心凭证">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>
        
        <el-form-item label="审查代号" prop="nickname">
          <el-input v-model="profileForm.nickname" placeholder="输入您的显示昵称" />
        </el-form-item>
        
        <el-form-item label="加密信道" prop="email">
          <el-input v-model="profileForm.email" placeholder="输入绑定的邮箱" />
        </el-form-item>
        
        <el-form-item label="生理构造" prop="gender">
          <el-radio-group v-model="profileForm.gender">
            <el-radio :label="0">保密</el-radio>
            <el-radio :label="1">男</el-radio>
            <el-radio :label="2">女</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="运转周期" prop="age">
          <el-input-number v-model="profileForm.age" :min="1" :max="120" placeholder="年龄" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <button class="cyber-btn-cancel" @click="profileDialogVisible = false">取消同步</button>
          <button class="submit-cyber-btn save-btn" @click="submitProfile" :disabled="isSavingProfile">
            {{ isSavingProfile ? 'UPLOADING...' : '确定' }}
          </button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { SwitchButton, ArrowLeft, ArrowRight, User } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import axios from 'axios'
import ReviewChat from '@/components/ReviewChat.vue'

const api = axios.create({ baseURL: '/api' })

const authStore = useAuthStore()
const router = useRouter()

const allTasks = ref([])
const currentTask = ref(null)
const filterType = ref('PENDING') 
const auditForm = ref({ result: '', comment: '' })
const isLoading = ref(false)

const totalTasks = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const pendingCount = ref(0)

const profileDialogVisible = ref(false)
const isSavingProfile = ref(false)
const profileFormRef = ref(null)
const profileForm = reactive({ username: authStore.username || '', nickname: '', email: '', gender: 0, age: null })

const fetchUserProfile = async () => {
  if (!authStore.username) return
  try {
    const res = await api.get(`/user/profile?username=${authStore.username}`)
    if (res.data.code === 200) Object.assign(profileForm, res.data.data)
  } catch (error) { console.error('获取审查员档案失败', error) }
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

const currentMediaIndex = ref(0)
const isVideo = (url) => url && /\.(mp4|mov|avi|webm)$/i.test(url)

// 直接解析带 _ 命名的 media_urls
const getMediaList = (task) => {
  if (!task) return []
  const list = []
  if (task.url) list.push(task.url)
  
  let parsedUrls = []
  try {
    if (task.media_urls) {
      parsedUrls = typeof task.media_urls === 'string' ? JSON.parse(task.media_urls) : task.media_urls
    }
  } catch (e) { console.error('媒体解析失败') }
  
  if (Array.isArray(parsedUrls)) list.push(...parsedUrls)
  return [...new Set(list)]
}

// 直接解析带 _ 命名的 saliency_urls
const getXaiList = (task) => {
  if (!task) return []
  let parsedUrls = []
  try {
    if (task.saliency_urls) {
      parsedUrls = typeof task.saliency_urls === 'string' ? JSON.parse(task.saliency_urls) : task.saliency_urls
    }
  } catch (e) { console.error('XAI解析失败') }
  return Array.isArray(parsedUrls) ? parsedUrls : []
}

const combinedMediaList = computed(() => {
  if (!currentTask.value) return []
  const originals = getMediaList(currentTask.value)
  const xais = getXaiList(currentTask.value)
  const result = []
  
  const maxLength = Math.max(originals.length, xais.length)
  for (let i = 0; i < maxLength; i++) {
    if (originals[i]) {
      result.push({ type: 'original', isVideo: isVideo(originals[i]), url: originals[i], label: isVideo(originals[i]) ? 'REC / VIDEO' : 'SOURCE / IMAGE' })
    }
    if (xais[i]) {
      result.push({ type: 'xai', isVideo: false, url: xais[i], label: `XAI MAP // ${i + 1}` })
    }
  }
  return result
})

const currentMediaItem = computed(() => combinedMediaList.value[currentMediaIndex.value] || {})
const prevMedia = () => { if (currentMediaIndex.value > 0) currentMediaIndex.value-- }
const nextMedia = () => { if (currentMediaIndex.value < combinedMediaList.value.length - 1) currentMediaIndex.value++ }

const changeTab = (type) => {
  filterType.value = type
  currentPage.value = 1
  currentTask.value = null
  fetchTasks()
}

const fetchTasks = async () => {
  try { 
    const res = await api.get(`/tasks?role=auditor&page=${currentPage.value}&size=${pageSize.value}&status_filter=${filterType.value}`)
    
    // 直接赋值，不做统一的数据映射
    if (res.data && res.data.code === 200) {
      allTasks.value = res.data.data.items
      totalTasks.value = res.data.data.total
      if (filterType.value === 'PENDING') { pendingCount.value = res.data.data.total }
    } else if (Array.isArray(res.data)) {
      const filtered = res.data.filter(t => filterType.value === 'PENDING' ? t.status !== 'audited' : t.status === 'audited')
      allTasks.value = filtered
      totalTasks.value = filtered.length
      if (filterType.value === 'PENDING') { pendingCount.value = filtered.length }
    }
  } 
  catch (e) { ElMessage.error('无法同步数据流') }
}

onMounted(() => { 
  fetchTasks()
  fetchUserProfile() 
})

const downloadTaskData = async () => {
  try {
    const res = await api.get('/export/tasks', {
      params: {
        role: 'auditor',
        status_filter: filterType.value
      },
      responseType: 'blob'
    })
    const blobUrl = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv;charset=utf-8;' }))
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = `auditor_tasks_${filterType.value.toLowerCase()}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(blobUrl)
    ElMessage.success({ message: '批量数据下载已开始', customClass: 'cyber-toast' })
  } catch (error) {
    ElMessage.error({ message: '下载失败，请稍后重试', customClass: 'cyber-toast' })
  }
}

// 取值时，严格使用带 _ 的字段
const selectTask = (task) => { 
  currentTask.value = task; 
  auditForm.value = { result: task.audit_result || '', comment: task.audit_comment || '' };
  currentMediaIndex.value = 0; 
}

const submitReview = async () => {
  if (!auditForm.value.result) return ElMessage.warning({message: '请指定裁决方向', customClass: 'cyber-toast'})
  isLoading.value = true
  try {
    await api.post('/audit_task', { task_id: currentTask.value.id, result: auditForm.value.result, comment: auditForm.value.comment })
    ElNotification({ title: 'SYNC SUCCESS', message: '数据已同步至模型演进队列', type: 'success', customClass: 'cyber-notice' })
    fetchTasks()
    currentTask.value = null
  } catch (e) { ElMessage.error('同步失败') }
  finally { isLoading.value = false }
}

const handleLogout = () => { if(authStore.logout) authStore.logout(); router.push('/login') }
</script>

<style scoped>
/* =========== 核心样式 =========== */
.zhixin-auditor { height: 100vh; background: #000; color: #fff; font-family: 'Inter', monospace; overflow: hidden; display: flex; flex-direction: column; }
.nexus-background { position: fixed; inset: 0; background: radial-gradient(circle at 50% 50%, #0a0f1a 0%, #000 100%); z-index: 0; }
.grid-layer { position: absolute; inset: 0; background-image: linear-gradient(rgba(0,242,254,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(0,242,254,0.02) 1px, transparent 1px); background-size: 50px 50px; }

/* =========== 头部导航 =========== */
.glass-header { position: relative; z-index: 10; display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; border-bottom: 1px solid rgba(0, 242, 254, 0.1); background: rgba(0,0,0,0.5); backdrop-filter: blur(10px); }
.brand-text { font-size: 16px; font-weight: 800; letter-spacing: 2px; }
.brand-text .light { color: #00f2fe; margin-left: 8px; font-weight: 300; }
.user-actions { display: flex; align-items: center; gap: 15px; }

.user-profile-trigger { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 8px; cursor: pointer; transition: 0.3s; background: rgba(255, 255, 255, 0.05); border: 1px solid transparent; }
.user-profile-trigger:hover { background: rgba(0, 242, 254, 0.1); border-color: rgba(0, 242, 254, 0.3); box-shadow: 0 0 10px rgba(0, 242, 254, 0.2); }
.user-icon { color: #00f2fe; font-size: 14px; }
.username { font-size: 12px; color: #e2e8f0; font-weight: 500; letter-spacing: 1px; }

.logout-btn { cursor: pointer; color: #fff; transition: 0.3s; opacity: 0.6; display: flex; align-items: center;}
.logout-btn:hover { opacity: 1; color: #f43f5e; transform: scale(1.1); }

/* =========== 整体布局 =========== */
.auditor-main { flex: 1; position: relative; z-index: 10; display: flex; gap: 20px; padding: 20px; overflow: hidden; }
.glass-panel { background: rgba(10, 15, 20, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; backdrop-filter: blur(20px); }
.panel-label { font-size: 10px; color: #00f2fe; letter-spacing: 2px; margin-bottom: 15px; border-bottom: 1px solid rgba(0,242,254,0.2); padding-bottom: 5px; }

/* =========== 左侧任务列表区 =========== */
.task-sidebar { width: 320px; display: flex; flex-direction: column; padding: 20px; }
.sidebar-header { margin-bottom: 20px; }
.title-row { display: flex; justify-content: space-between; font-size: 12px; font-weight: 800; color: #a0aec0; margin-bottom: 15px; }
.sidebar-actions { display: flex; align-items: center; gap: 10px; }
.download-btn { border: 1px solid rgba(0,242,254,0.35); background: rgba(0,242,254,0.08); color: #00f2fe; border-radius: 8px; padding: 6px 10px; font-size: 11px; font-weight: 700; cursor: pointer; transition: 0.3s; }
.download-btn:hover { background: rgba(0,242,254,0.16); box-shadow: 0 0 12px rgba(0,242,254,0.2); }
.cyber-tabs { display: flex; background: rgba(0,0,0,0.5); border-radius: 8px; padding: 4px; }
.tab { flex: 1; text-align: center; font-size: 12px; padding: 6px; cursor: pointer; border-radius: 6px; color: #718096; transition: 0.3s; }
.tab.active { background: #00f2fe; color: #000; font-weight: 800; }
/* 列表与重叠修复 */
.task-list { flex: 1; overflow-y: auto; padding-right: 5px; display: flex; flex-direction: column; gap: 10px; min-height: 0; }
.task-list::-webkit-scrollbar { width: 4px; }
.task-list::-webkit-scrollbar-thumb { background: rgba(0,242,254,0.2); }
.empty-history { text-align: center; color: #718096; font-size: 12px; margin-top: 20px; }

.cyber-task-card { position: relative; padding: 15px; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; cursor: pointer; transition: 0.3s; overflow: hidden; flex-shrink: 0; }
.cyber-task-card:hover { border-color: rgba(0,242,254,0.5); transform: translateX(5px); }
.cyber-task-card.active { border-color: #00f2fe; background: rgba(0,242,254,0.05); }
.card-glow { position: absolute; left: 0; top: 0; height: 100%; width: 3px; background: #00f2fe; opacity: 0; transition: 0.3s; }
.cyber-task-card.active .card-glow { opacity: 1; }
.task-id { font-size: 10px; color: #00f2fe; margin-bottom: 5px; }

.engine-tiny-tag { font-size: 9px; padding: 1px 4px; border-radius: 3px; font-weight: bold; margin-right: 4px; border: 1px solid; }
.fast-tag { color: #00f2fe; border-color: rgba(0,242,254,0.5); background: rgba(0,242,254,0.1); }
.pro-tag { color: #a855f7; border-color: rgba(168,85,247,0.5); background: rgba(168,85,247,0.1); }
.pro-mllm-tag { background: rgba(168, 85, 247, 0.2); color: #a855f7; border: 1px solid #a855f7; font-weight: bold; }

.task-title { font-size: 13px; font-weight: 500; margin-bottom: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; }
.task-meta { display: flex; justify-content: space-between; align-items: center; }
.cyber-tag { font-size: 9px; padding: 2px 6px; background: rgba(255,255,255,0.1); border-radius: 4px; margin-right: 4px; }
.xai-tag { background: rgba(244, 63, 94, 0.2); color: #f43f5e; border: 1px solid #f43f5e; font-weight: bold; }
.score { font-size: 14px; font-weight: 800; }
.score.danger { color: #f43f5e; }
.score.safe { color: #10b981; }

/* 审核员分页器样式 */
.pagination-wrapper { display: flex; justify-content: center; margin-top: 15px; padding-top: 15px; border-top: 1px dashed rgba(255,255,255,0.1); }
.cyber-pagination { --el-pagination-bg-color: rgba(0,0,0,0.4); --el-pagination-text-color: #a0aec0; --el-pagination-hover-color: #00f2fe; }
.cyber-pagination :deep(.el-pager li) { border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; background: transparent; margin: 0 3px;}
.cyber-pagination :deep(.el-pager li.is-active) { background: rgba(0, 242, 254, 0.2); color: #00f2fe; border-color: #00f2fe; font-weight: 900; box-shadow: 0 0 10px rgba(0,242,254,0.3); }
.cyber-pagination :deep(button) { background: transparent !important; color: #718096 !important; }
.cyber-pagination :deep(button:disabled) { opacity: 0.3; }

/* =========== 右侧审核工作区 =========== */
.review-workspace { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.workspace-grid { display: grid; grid-template-columns: 1fr 380px; gap: 20px; height: 100%; overflow: hidden; }
.media-carousel-panel { display: flex; flex-direction: column; padding: 20px; height: 100%; overflow: hidden; }
.carousel-container { flex: 1; display: flex; align-items: center; justify-content: space-between; gap: 15px; position: relative; min-height: 0; }
.nav-btn { flex-shrink: 0; width: 44px; height: 44px; background: rgba(0,242,254,0.1); border: 1px solid #00f2fe; color: #00f2fe; border-radius: 50%; display: flex; justify-content: center; align-items: center; cursor: pointer; transition: 0.3s; z-index: 10;}
.nav-btn:hover:not(:disabled) { background: #00f2fe; color: #000; box-shadow: 0 0 15px rgba(0,242,254,0.6); }
.nav-btn:disabled { border-color: rgba(255,255,255,0.1); color: rgba(255,255,255,0.2); background: transparent; cursor: not-allowed; }
.media-frame { flex: 1; height: 100%; background: #000; border: 1px solid rgba(0,242,254,0.2); position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 10px; box-sizing: border-box; }
.media-content { max-width: 100%; max-height: 100%; object-fit: contain; z-index: 1; }
.frame-corner { position: absolute; width: 15px; height: 15px; border: 2px solid #00f2fe; }
.top-left { top: 0; left: 0; border-right: none; border-bottom: none; }
.top-right { top: 0; right: 0; border-left: none; border-bottom: none; }
.bottom-left { bottom: 0; left: 0; border-right: none; border-top: none; }
.bottom-right { bottom: 0; right: 0; border-left: none; border-top: none; }
.frame-label { position: absolute; top: 15px; right: 15px; font-size: 11px; font-weight: bold; background: rgba(0,0,0,0.8); color: #00f2fe; padding: 4px 8px; z-index: 2; border: 1px solid #00f2fe; }
.counter { color: rgba(255,255,255,0.5); font-weight: normal; margin-left: 5px; }
.empty-media { height: 100%; display: flex; align-items: center; justify-content: center; color: rgba(0,242,254,0.5); font-weight: 800; letter-spacing: 2px; }

/* XAI 热力图特效 */
.xai-frame { border-color: rgba(244, 63, 94, 0.4); box-shadow: inset 0 0 40px rgba(244, 63, 94, 0.1); }
.xai-corner { border-color: #f43f5e; }
.xai-label { background: rgba(244, 63, 94, 0.9); color: #fff; border-color: #f43f5e; }
.scan-line { position: absolute; top: 0; left: 0; width: 100%; height: 2px; background: rgba(244,63,94,0.8); box-shadow: 0 0 15px #f43f5e; animation: scanDown 3s infinite linear; pointer-events: none; z-index: 5; }
@keyframes scanDown { 0% { top: 0; opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { top: 100%; opacity: 0; } }

/* 右侧侧边栏区 */
.right-column { display: flex; flex-direction: column; gap: 20px; height: 100%; overflow-y: auto; padding-right: 4px; }
.right-column::-webkit-scrollbar { width: 4px; }
.right-column::-webkit-scrollbar-thumb { background: rgba(0,242,254,0.25); border-radius: 2px; }
.text-panel { flex: 0 0 210px; padding: 20px; display: flex; flex-direction: column; min-height: 0; }
.cyber-text-box { flex: 1; background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; font-size: 13px; line-height: 1.6; color: #e2e8f0; overflow-y: auto; border: 1px solid rgba(255,255,255,0.05); }
.cyber-text-box::-webkit-scrollbar { width: 4px; }
.cyber-text-box::-webkit-scrollbar-thumb { background: rgba(0,242,254,0.3); }

/* 决策与意见区 */
.decision-panel { flex-shrink: 0; padding: 20px; display: flex; flex-direction: column; height: auto; }
.auditor-chat { flex: 0 0 320px; min-height: 320px; }

/* 将提示框变为 flex 列布局，让头部标题固定，内容区滚动 */
.ai-suggestion { background: rgba(0,0,0,0.3); padding: 15px; border-left: 3px solid; border-radius: 8px; margin-bottom: 20px; display: flex; flex-direction: column; }

/* 当判断出这是一个 Pro 模型的推演结果时，改变提示框样式 */
.ai-suggestion.is-pro-suggestion { border-left-color: #a855f7; background: rgba(168,85,247,0.05); }
.ai-suggestion.is-pro-suggestion .sugg-header { color: #a855f7; font-weight: bold; }
.ai-suggestion.is-pro-suggestion .sugg-body { color: #e2e8f0; line-height: 1.6; }

.ai-suggestion.alert:not(.is-pro-suggestion) { border-color: #f43f5e; }
.ai-suggestion.pass:not(.is-pro-suggestion) { border-color: #10b981; }

/* 头部标题禁止被压缩 */
.sugg-header { font-size: 10px; color: #a0aec0; margin-bottom: 8px; flex-shrink: 0; }

/* 👇 核心修复：限制最大高度，并开启独立的赛博滚动条 */
.sugg-body { 
  font-size: 12px; 
  color: #fff; 
  max-height: 160px;  /* 缩小纵向占比，保护上方语义层和下方操作区 */
  overflow-y: auto;   /* 开启内部垂直滑动 */
  padding-right: 8px; 
}

/* 为推演报告定制专属的纤细赛博滚动条 */
.sugg-body::-webkit-scrollbar { width: 4px; }
.sugg-body::-webkit-scrollbar-thumb { background: rgba(0,242,254,0.3); border-radius: 2px; }
/* 如果是 PRO 引擎，滚动条变成尊贵的紫色 */
.ai-suggestion.is-pro-suggestion .sugg-body::-webkit-scrollbar-thumb { background: rgba(168,85,247,0.4); }

/* 下方的裁决单选框和输入区保持不变 */
.radio-cyber { display: flex; gap: 10px; margin-bottom: 15px; }
.radio-label input { display: none; }
.custom-radio { flex: 1; text-align: center; padding: 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 800; transition: 0.3s; }
.radio-label input:checked + .custom-radio.real { background: rgba(16,185,129,0.2); border-color: #10b981; color: #10b981; }
.radio-label input:checked + .custom-radio.fake { background: rgba(244,63,94,0.2); border-color: #f43f5e; color: #f43f5e; }

.cyber-input { width: 100%; background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); padding: 12px; color: #fff; border-radius: 8px; font-size: 12px; outline: none; transition: 0.3s; margin-bottom: 15px; box-sizing: border-box;}
.cyber-input:focus { border-color: #00f2fe; }

.submit-cyber-btn { width: 100%; padding: 15px; background: #00f2fe; border: none; border-radius: 8px; color: #000; font-weight: 800; font-size: 12px; cursor: pointer; transition: 0.3s; }
.submit-cyber-btn:hover:not(:disabled) { box-shadow: 0 0 20px rgba(0,242,254,0.4); transform: translateY(-2px); }
.submit-cyber-btn:disabled { background: #334155; color: #94a3b8; cursor: not-allowed; }
.standby-screen { flex: 1; display: flex; align-items: center; justify-content: center; flex-direction: column; opacity: 0.5; }
.crosshair { width: 40px; height: 40px; border: 1px solid #00f2fe; position: relative; margin-bottom: 20px; animation: spin 10s linear infinite; }
.crosshair::before, .crosshair::after { content: ''; position: absolute; background: #00f2fe; }
.crosshair::before { top: 50%; left: -10px; right: -10px; height: 1px; }
.crosshair::after { left: 50%; top: -10px; bottom: -10px; width: 1px; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.danger-tag { background: rgba(244, 63, 94, 0.2); color: #f43f5e; border: 1px solid #f43f5e; }
.safe-tag { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
.submit-cyber-btn.is-update { background: transparent; border: 1px solid #f59e0b; color: #f59e0b; }
.submit-cyber-btn.is-update:hover { background: rgba(245, 158, 11, 0.1); box-shadow: 0 0 20px rgba(245, 158, 11, 0.4); }

/* 全局覆盖消息气泡 */
:global(.cyber-toast) { background: rgba(10, 15, 20, 0.9) !important; border: 1px solid #00f2fe !important; backdrop-filter: blur(10px) !important; color: #fff !important; font-family: 'Inter', monospace !important; border-radius: 8px !important; }

/* =========== 个人档案弹窗区 =========== */
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
.submit-cyber-btn.save-btn { width: auto; padding: 0 25px; height: 38px; background: transparent; border: 1px solid #00f2fe; color: #00f2fe; }
.submit-cyber-btn.save-btn:hover { background: #00f2fe; color: #000; }
</style>
