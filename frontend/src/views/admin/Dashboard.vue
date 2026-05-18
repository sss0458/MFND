<template>
  <div class="zhixin-admin-portal">
    <div class="cyber-background">
      <div class="glow-orb orb-primary"></div>
      <div class="glow-orb orb-secondary"></div>
      <div class="grid-overlay"></div>
    </div>

    <header class="glass-header">
      <div class="brand-logo">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#00f2fe" stroke-width="2" stroke-linejoin="round"/>
          <path d="M2 17L12 22L22 17" stroke="#00f2fe" stroke-width="2" stroke-linejoin="round"/>
          <path d="M2 12L12 17L22 12" stroke="#4facfe" stroke-width="2" stroke-linejoin="round"/>
        </svg>
        <span class="brand-text">智信未来 <span class="light">COMMAND CENTER</span></span>
      </div>
      <div class="user-actions">
        <button class="header-download-btn" @click="downloadTaskData">下载任务数据</button>
        <button class="header-download-btn secondary" @click="downloadUserData">下载用户数据</button>
        <div class="role-badge">
          <span class="pulse-dot"></span> SYSTEM ADMIN
        </div>
        
        <div class="user-profile-trigger" @click="openProfileDialog">
          <el-icon class="user-icon"><User /></el-icon>
          <span class="username">{{ profileForm.nickname || authStore.username || 'Administrator' }}</span>
        </div>

        <div class="logout-btn" @click="handleLogout" title="断开连接">
          <el-icon><SwitchButton /></el-icon>
        </div>
      </div>
    </header>

    <div class="main-content">
      <el-row :gutter="24" class="stat-row">
        <el-col :span="6">
          <div class="cyber-stat-card">
            <div class="card-glow primary"></div>
            <div class="stat-header">🚀 实时算力 (GFLOPs)</div>
            <div class="stat-body">
              <span class="stat-value">{{ realtimeMetrics.gflops }}</span>
              <span class="stat-unit">T</span>
            </div>
            <div class="stat-footer">Peak Threshold: 14.2 T</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="cyber-stat-card">
            <div class="card-glow warning"></div>
            <div class="stat-header">💾 显存负载 (VRAM)</div>
            <div class="stat-body warning-text">
              <span class="stat-value">{{ realtimeMetrics.vram }}</span>
              <span class="stat-unit">GB</span>
            </div>
            <div class="stat-progress">
              <div class="progress-track">
                <div class="progress-fill warning-bg" :style="{ width: realtimeMetrics.vramPercent + '%' }"></div>
              </div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="cyber-stat-card">
            <div class="card-glow success"></div>
            <div class="stat-header">⚡ 推理延迟 (Latency)</div>
            <div class="stat-body success-text">
              <span class="stat-value">{{ realtimeMetrics.latency }}</span>
              <span class="stat-unit">ms</span>
            </div>
            <div class="stat-footer">Target SLA: &lt; 50ms</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="cyber-stat-card">
            <div class="card-glow info"></div>
            <div class="stat-header">👥 今日审核流</div>
            <div class="stat-body info-text">
              <span class="stat-value">1,024</span>
              <span class="stat-unit">Tasks</span>
            </div>
            <div class="stat-footer">+12% vs Yesterday (Active)</div>
          </div>
        </el-col>
      </el-row>

      <div class="glass-panel workspace-panel">
        <el-tabs v-model="activeTab" class="cyber-tabs">
          
          <el-tab-pane label="📊 算法性能评估 (Model Eval)" name="eval">
            <el-row :gutter="24">
              <el-col :span="16">
                <div class="chart-box">
                  <div class="chart-title">
                    <span class="title-icon"></span> 引擎资源占用与延迟趋势 (Real-time Monitoring)
                  </div>
                  <div ref="lineChartRef" class="echart-container"></div>
                </div>
              </el-col>
              
              <el-col :span="8">
                <div class="chart-box">
                  <div class="chart-title"><span class="title-icon"></span> 测试集基准 (Test Set Metrics)</div>
                  <div class="metrics-list">
                    <div class="metric-item">
                      <el-progress type="dashboard" :percentage="94.5" color="#00f2fe" :width="100">
                        <template #default="{ percentage }">
                          <span class="percentage-value">{{ percentage }}%</span>
                          <span class="percentage-label">Accuracy</span>
                        </template>
                      </el-progress>
                    </div>
                    <div class="metric-item">
                      <el-progress type="dashboard" :percentage="92.1" color="#4facfe" :width="100">
                        <template #default="{ percentage }">
                          <span class="percentage-value">0.92</span>
                          <span class="percentage-label">F1-Score</span>
                        </template>
                      </el-progress>
                    </div>
                  </div>
                </div>
                
                <div class="chart-box" style="margin-top: 20px; height: 320px;">
                   <div class="chart-title"><span class="title-icon"></span> 混淆矩阵 (Confusion Matrix)</div>
                   <div ref="heatmapRef" class="echart-container"></div>
                </div>
              </el-col>
            </el-row>
          </el-tab-pane>

          <el-tab-pane label="👮 用户权限控制 (User Manage)" name="users">
            <UserManage />  
          </el-tab-pane>

          <el-tab-pane label="⚙️ 核心引擎调度 (Engine Control)" name="engines">
            <div class="engine-control-wrapper">
              <div class="control-header">
                <div class="warning-text"><el-icon><WarningFilled /></el-icon> SYSTEM OVERRIDE ACTIVE</div>
                <p>管理员可在此处强制切断或恢复底层算力引擎的公共访问权限。断开连接将导致前端节点触发降级策略。</p>
              </div>

              <div class="engine-cards-grid">
                <div class="engine-control-card" :class="{ 'is-offline': !engineStatus.fast }">
                  <div class="card-bg-glow"></div>
                  <div class="engine-info">
                    <div class="engine-icon fast-icon"><el-icon><Lightning /></el-icon></div>
                    <div class="engine-details">
                      <div class="engine-name">FAST ENGINE <span>v2.1</span></div>
                      <div class="engine-desc">ViT + RoBERTa 毫秒级多模态特征融合对齐</div>
                      <div class="engine-status-label" :class="engineStatus.fast ? 'online' : 'offline'">
                        {{ engineStatus.fast ? '🟢 STATUS: ONLINE / 正常运转' : '🔴 STATUS: OFFLINE / 维护中' }}
                      </div>
                    </div>
                  </div>
                  <div class="engine-action">
                    <el-switch
                      v-model="engineStatus.fast"
                      inline-prompt
                      active-text="ON"
                      inactive-text="OFF"
                      class="cyber-switch fast-switch"
                      @change="(val) => handleEngineToggle('fast', val)"
                    />
                  </div>
                </div>

                <div class="engine-control-card" :class="{ 'is-offline': !engineStatus.pro }">
                  <div class="card-bg-glow pro-glow"></div>
                  <div class="engine-info">
                    <div class="engine-icon pro-icon"><el-icon><Cpu /></el-icon></div>
                    <div class="engine-details">
                      <div class="engine-name">PRO ENGINE <span>(CMIE)</span></div>
                      <div class="engine-desc">MLLM 语义逻辑推演与图文共存关系分析 (高算力消耗)</div>
                      <div class="engine-status-label" :class="engineStatus.pro ? 'online' : 'offline'">
                        {{ engineStatus.pro ? '🟢 STATUS: ONLINE / 正常运转' : '🔴 STATUS: OFFLINE / 降级熔断' }}
                      </div>
                    </div>
                  </div>
                  <div class="engine-action">
                    <el-switch
                      v-model="engineStatus.pro"
                      inline-prompt
                      active-text="ON"
                      inactive-text="OFF"
                      class="cyber-switch pro-switch"
                      @change="(val) => handleEngineToggle('pro', val)"
                    />
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

        </el-tabs>
      </div>
    </div>

    <el-dialog 
      v-model="profileDialogVisible" 
      title="中枢控制者档案 // ADMIN PROFILE" 
      width="420px" 
      class="cyber-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="profileForm" ref="profileFormRef" label-width="90px" class="cyber-form">
        <el-form-item label="核心凭证">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>
        
        <el-form-item label="最高代号" prop="nickname">
          <el-input v-model="profileForm.nickname" placeholder="输入您的指令代号" />
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
        
        <el-form-item label="权限周期" prop="age">
          <el-input-number v-model="profileForm.age" :min="1" :max="120" placeholder="年龄" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <button class="cyber-btn-cancel" @click="profileDialogVisible = false">ABORT</button>
          <button class="cyber-btn-solid save-btn" @click="submitProfile" :disabled="isSavingProfile">
            {{ isSavingProfile ? 'SYNCING...' : 'OVERWRITE / 覆写核心' }}
          </button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import * as echarts from 'echarts'
// 👇 引入所需的图标
import { SwitchButton, User, Lightning, Cpu, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios' 
import UserManage from './UserManage.vue'
import { getSystemStats } from '@/api/monitor' 

const router = useRouter()
const authStore = useAuthStore()
const api = axios.create({ baseURL: '/api' })

const activeTab = ref('eval') // 默认停留在性能评估 Tab
const realtimeMetrics = reactive({ gflops: 0, vram: 0, vramPercent: 0, latency: 0 })

// ================= 新增：引擎状态管理逻辑 =================
// 在实际项目中，这里会从后端的配置表拉取。这里用布尔值表示：true=在线，false=离线
const engineStatus = reactive({
  fast: true,
  pro: false // 模拟默认把消耗大的 Pro 模型给关了
})

// 页面加载时从后端拉取真实状态
const fetchEngineStatus = async () => {
  try {
    const res = await api.get('/system/engine_status')
    if (res.data.code === 200) {
      engineStatus.fast = res.data.data.fast
      engineStatus.pro = res.data.data.pro
    }
  } catch (error) {
    console.error('获取引擎状态失败', error)
  }
}

// 拨动开关时，将指令发送给后端
const handleEngineToggle = async (engine, val) => {
  try {
    const res = await api.put('/system/engine_status', {
      engine: engine,
      status: val
    })
    
    if (res.data.code === 200) {
      const statusText = val ? 'ONLINE / 恢复访问' : 'OFFLINE / 已物理切断'
      ElMessage.success({ 
        message: `[${engine.toUpperCase()} ENGINE] ${statusText}`, 
        customClass: 'cyber-toast' 
      })
    }
  } catch (error) {
    // 如果后端报错或断网，UI 状态回滚防呆
    engineStatus[engine] = !val
    ElMessage.error({ message: '指令执行失败，网络异常', customClass: 'cyber-toast' })
  }
}

// =========================================================

// 个人信息管理逻辑
const profileDialogVisible = ref(false)
const isSavingProfile = ref(false)
const profileFormRef = ref(null)
const profileForm = reactive({ username: authStore.username || '', nickname: '', email: '', gender: 0, age: null })

const fetchUserProfile = async () => {
  if (!authStore.username) return
  try {
    const res = await api.get(`/user/profile?username=${authStore.username}`)
    if (res.data.code === 200) Object.assign(profileForm, res.data.data)
  } catch (error) { console.error('获取Admin档案失败', error) }
}

const openProfileDialog = () => { profileDialogVisible.value = true }
const submitProfile = async () => {
  isSavingProfile.value = true
  try {
    const res = await api.put('/user/profile', profileForm)
    if (res.data.code === 200) { ElMessage.success({ message: 'ADMIN DATA OVERWRITTEN / 管理员数据已覆写', customClass: 'cyber-toast' }); profileDialogVisible.value = false }
  } catch (error) { ElMessage.error({ message: '更新失败，请检查网络连接', customClass: 'cyber-toast' }) }
  finally { isSavingProfile.value = false }
}

const downloadBlob = (blobData, filename) => {
  const blobUrl = window.URL.createObjectURL(new Blob([blobData], { type: 'text/csv;charset=utf-8;' }))
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(blobUrl)
}

const downloadTaskData = async () => {
  try {
    const res = await api.get('/export/tasks', {
      params: { role: 'admin' },
      responseType: 'blob'
    })
    downloadBlob(res.data, 'admin_tasks.csv')
    ElMessage.success({ message: '任务数据下载已开始', customClass: 'cyber-toast' })
  } catch (error) {
    ElMessage.error({ message: '任务数据下载失败', customClass: 'cyber-toast' })
  }
}

const downloadUserData = async () => {
  try {
    const res = await api.get('/export/users', { responseType: 'blob' })
    downloadBlob(res.data, 'admin_users.csv')
    ElMessage.success({ message: '用户数据下载已开始', customClass: 'cyber-toast' })
  } catch (error) {
    ElMessage.error({ message: '用户数据下载失败', customClass: 'cyber-toast' })
  }
}

const lineChartRef = ref(null)
const heatmapRef = ref(null)
let lineChart = null
let heatmapChart = null
let timer = null

const initLineChart = () => {
  if (!lineChartRef.value) return
  lineChart = echarts.init(lineChartRef.value)
  const xData = Array.from({length: 20}, () => new Date().toLocaleTimeString('en-US', {hour12: false}))
  const vramData = new Array(20).fill(0)
  const latencyData = new Array(20).fill(0)
  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(10, 12, 16, 0.8)', borderColor: '#00f2fe', textStyle: { color: '#fff' } },
    legend: { data: ['VRAM (GB)', 'Latency (ms)'], textStyle: { color: '#a0aec0' }, top: 0 },
    grid: { left: '2%', right: '2%', bottom: '2%', top: '15%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: xData, axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }, axisLabel: { color: '#718096', fontFamily: 'monospace' } },
    yAxis: [
      { type: 'value', min: 0, max: 24, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' } }, axisLabel: { color: '#718096', fontFamily: 'monospace' } },
      { type: 'value', min: 0, max: 100, splitLine: { show: false }, axisLabel: { color: '#718096', fontFamily: 'monospace' } }
    ],
    series: [
      { name: 'VRAM (GB)', type: 'line', smooth: true, data: vramData, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{offset: 0, color: 'rgba(0, 242, 254, 0.4)'}, {offset: 1, color: 'rgba(0, 242, 254, 0)'}]) }, itemStyle: { color: '#00f2fe' }, lineStyle: { width: 2, shadowColor: '#00f2fe', shadowBlur: 10 } },
      { name: 'Latency (ms)', type: 'line', smooth: true, yAxisIndex: 1, data: latencyData, itemStyle: { color: '#10b981' }, lineStyle: { width: 2, shadowColor: '#10b981', shadowBlur: 10 } }
    ]
  }
  lineChart.setOption(option)
}

const initHeatmap = () => {
  if (!heatmapRef.value) return
  heatmapChart = echarts.init(heatmapRef.value)
  const data = [[0,0, 450], [0,1, 23], [1,0, 45], [1,1, 482]]
  const option = {
    backgroundColor: 'transparent',
    tooltip: { position: 'top', backgroundColor: 'rgba(10, 12, 16, 0.8)', borderColor: '#4facfe', textStyle: { color: '#fff' } },
    grid: { left: '15%', right: '5%', bottom: '15%', top: '5%' },
    xAxis: { type: 'category', data: ['Pred: Real', 'Pred: Fake'], axisLabel: { color: '#a0aec0' }, axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
    yAxis: { type: 'category', data: ['True: Real', 'True: Fake'], axisLabel: { color: '#a0aec0' }, axisLine: { show: false } },
    visualMap: { min: 0, max: 500, calculable: true, orient: 'horizontal', left: 'center', bottom: '0%', textStyle: { color: '#718096' }, inRange: { color: ['rgba(0, 242, 254, 0.1)', '#00f2fe'] } },
    series: [{ name: 'Confusion Matrix', type: 'heatmap', data: data, label: { show: true, color: '#fff', fontSize: 16, fontWeight: 'bold' }, itemStyle: { borderColor: '#030305', borderWidth: 2 } }]
  }
  heatmapChart.setOption(option)
}

const startMonitoring = () => {
  timer = setInterval(async () => {
    try {
      const res = await getSystemStats()
      const data = res.data
      realtimeMetrics.gflops = data.gflops
      realtimeMetrics.vram = data.vram
      realtimeMetrics.vramPercent = Math.min(Math.floor((data.vram / 24) * 100), 100)
      realtimeMetrics.latency = data.latency

      if (lineChart) {
        const axisData = new Date().toLocaleTimeString('en-US', {hour12: false})
        const option = lineChart.getOption()
        const dataVram = option.series[0].data; const dataLat = option.series[1].data; const dataX = option.xAxis[0].data
        dataVram.shift(); dataVram.push(data.vram); dataLat.shift(); dataLat.push(data.latency); dataX.shift(); dataX.push(axisData)
        lineChart.setOption({ xAxis: { data: dataX }, series: [{ data: dataVram }, { data: dataLat }] })
      }
    } catch (error) { console.error("Monitor Sync Failed:", error) }
  }, 2000)
}

onMounted(() => {
  setTimeout(() => { initLineChart(); initHeatmap(); startMonitoring() }, 100)
  fetchUserProfile()
  fetchEngineStatus()
  window.addEventListener('resize', () => { lineChart && lineChart.resize(); heatmapChart && heatmapChart.resize() })
})

onUnmounted(() => { if (timer) clearInterval(timer) })

const handleLogout = () => {
  if (authStore.logout) authStore.logout() 
  ElMessage({ message: 'SYSTEM CONNECTION TERMINATED', type: 'success', customClass: 'cyber-toast' })
  router.push('/login')
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&display=swap');

/* --- 保持原有的暗黑布局和组件样式不变 --- */
.zhixin-admin-portal { min-height: 100vh; background-color: #030305; color: #fff; font-family: 'Inter', sans-serif; position: relative; overflow-x: hidden; }
.cyber-background { position: fixed; inset: 0; pointer-events: none; z-index: 0; }
.glow-orb { position: absolute; border-radius: 50%; filter: blur(150px); opacity: 0.4; animation: floatOrb 20s infinite alternate ease-in-out; }
.orb-primary { width: 50vw; height: 50vw; background: #00f2fe; top: -20vw; right: -10vw; }
.orb-secondary { width: 40vw; height: 40vw; background: #4facfe; bottom: -10vw; left: -10vw; animation-delay: -5s; opacity: 0.2; }
.grid-overlay { position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px); background-size: 50px 50px; }
@keyframes floatOrb { 0% { transform: translate(0, 0); } 100% { transform: translate(-30px, 30px); } }

.glass-header { position: relative; z-index: 10; display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: rgba(10, 12, 16, 0.4); backdrop-filter: blur(20px); border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
.brand-logo { display: flex; align-items: center; gap: 12px; }
.logo-icon { width: 28px; height: 28px; }
.brand-text { font-size: 18px; font-weight: 800; letter-spacing: 2px; }
.brand-text .light { font-weight: 300; color: #a0aec0; margin-left: 8px; font-size: 13px; }

.user-actions { display: flex; align-items: center; gap: 20px; }
.header-download-btn { border: 1px solid rgba(0,242,254,0.28); background: rgba(0,242,254,0.08); color: #00f2fe; border-radius: 8px; padding: 8px 12px; font-size: 12px; font-weight: 700; cursor: pointer; transition: 0.3s; }
.header-download-btn.secondary { color: #a5b4fc; border-color: rgba(165,180,252,0.28); background: rgba(165,180,252,0.08); }
.header-download-btn:hover { transform: translateY(-1px); box-shadow: 0 0 12px rgba(0,242,254,0.16); }
.role-badge { display: flex; align-items: center; gap: 8px; font-size: 11px; font-weight: 800; color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.3); padding: 4px 10px; border-radius: 20px; background: rgba(244, 63, 94, 0.1); letter-spacing: 1px; }
.pulse-dot { width: 6px; height: 6px; background: #f43f5e; border-radius: 50%; box-shadow: 0 0 8px #f43f5e; animation: blink 1.5s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.user-profile-trigger { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 8px; cursor: pointer; transition: 0.3s; background: rgba(255, 255, 255, 0.05); border: 1px solid transparent; }
.user-profile-trigger:hover { background: rgba(0, 242, 254, 0.1); border-color: rgba(0, 242, 254, 0.3); box-shadow: 0 0 10px rgba(0, 242, 254, 0.2); }
.user-icon { color: #00f2fe; font-size: 14px; }
.username { font-size: 13px; color: #a0aec0; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;}
.logout-btn { cursor: pointer; color: #fff; opacity: 0.6; transition: 0.3s; font-size: 18px; }
.logout-btn:hover { opacity: 1; color: #f43f5e; transform: scale(1.1); }

.main-content { position: relative; z-index: 10; padding: 40px; max-width: 1600px; margin: 0 auto; }
.stat-row { margin-bottom: 30px; }
.cyber-stat-card { background: rgba(10, 12, 16, 0.6); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 25px; position: relative; overflow: hidden; transition: 0.4s; }
.cyber-stat-card:hover { transform: translateY(-5px); border-color: rgba(255,255,255,0.2); }
.card-glow { position: absolute; top: 0; left: 0; width: 100%; height: 3px; }
.card-glow.primary { background: #00f2fe; box-shadow: 0 0 15px #00f2fe; }
.card-glow.warning { background: #f59e0b; box-shadow: 0 0 15px #f59e0b; }
.card-glow.success { background: #10b981; box-shadow: 0 0 15px #10b981; }
.card-glow.info { background: #8b5cf6; box-shadow: 0 0 15px #8b5cf6; }
.stat-header { font-size: 12px; color: #a0aec0; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 15px; }
.stat-body { display: flex; align-items: baseline; gap: 8px; font-family: 'Inter', monospace; }
.stat-value { font-size: 42px; font-weight: 900; line-height: 1; }
.stat-unit { font-size: 14px; color: #718096; font-weight: 700; }
.primary-text { color: #00f2fe; }
.warning-text { color: #f59e0b; }
.success-text { color: #10b981; }
.info-text { color: #8b5cf6; }
.stat-footer { font-size: 11px; color: #4a5568; margin-top: 15px; font-family: monospace; letter-spacing: 0.5px; }
.stat-progress { margin-top: 15px; }
.progress-track { width: 100%; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; transition: width 0.5s ease; }
.warning-bg { background: #f59e0b; box-shadow: 0 0 10px #f59e0b; }
.glass-panel { background: rgba(10, 12, 16, 0.4); backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 30px; }
.cyber-tabs :deep(.el-tabs__nav-wrap::after) { height: 1px; background-color: rgba(255,255,255,0.1); }
.cyber-tabs :deep(.el-tabs__item) { color: #718096; font-size: 15px; font-weight: 700; letter-spacing: 1px; height: 50px; }
.cyber-tabs :deep(.el-tabs__item.is-active) { color: #00f2fe; }
.cyber-tabs :deep(.el-tabs__active-bar) { background-color: #00f2fe; box-shadow: 0 0 10px #00f2fe; height: 3px; }
.chart-box { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; height: 100%; display: flex; flex-direction: column; }
.chart-title { font-size: 13px; font-weight: 700; color: #e2e8f0; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; letter-spacing: 1px; }
.title-icon { width: 4px; height: 14px; background: #00f2fe; border-radius: 2px; box-shadow: 0 0 8px #00f2fe; }
.echart-container { flex: 1; width: 100%; min-height: 350px; }
.metrics-list { display: flex; justify-content: space-around; align-items: center; height: 100%; }
.metric-item { display: flex; flex-direction: column; align-items: center; justify-content: center; }
.percentage-value { display: block; font-size: 24px; font-weight: 900; color: #fff; font-family: monospace; }
.percentage-label { display: block; font-size: 11px; color: #718096; text-transform: uppercase; margin-top: 5px; letter-spacing: 1px; }
.metric-item :deep(.el-progress-circle__track) { stroke: rgba(255,255,255,0.05) !important; }

/* =======================================================
   👇 新增：核心引擎调度 (Engine Control) 专属样式 
======================================================= */
.engine-control-wrapper { padding: 10px; }
.control-header { margin-bottom: 30px; }
.control-header .warning-text { color: #f43f5e; font-weight: 900; letter-spacing: 1px; font-size: 14px; display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.control-header p { color: #718096; font-size: 13px; margin: 0; line-height: 1.5; }

.engine-cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.engine-control-card { 
  background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; 
  padding: 25px; display: flex; justify-content: space-between; align-items: center; 
  position: relative; overflow: hidden; transition: 0.4s;
}
.engine-control-card:hover { transform: translateY(-3px); }
.card-bg-glow { position: absolute; left: 0; top: 0; height: 100%; width: 4px; background: #00f2fe; box-shadow: 0 0 15px #00f2fe; transition: 0.4s; }
.pro-glow { background: #a855f7; box-shadow: 0 0 15px #a855f7; }

/* 断电 (Offline) 状态样式 */
.engine-control-card.is-offline { border-color: rgba(244, 63, 94, 0.3); background: rgba(244, 63, 94, 0.02); filter: grayscale(80%); opacity: 0.8; }
.engine-control-card.is-offline .card-bg-glow { background: #f43f5e; box-shadow: 0 0 15px #f43f5e; opacity: 0.5;}

.engine-info { display: flex; align-items: center; gap: 20px; }
.engine-icon { width: 50px; height: 50px; border-radius: 12px; display: flex; justify-content: center; align-items: center; font-size: 24px; }
.fast-icon { background: rgba(0, 242, 254, 0.1); color: #00f2fe; border: 1px solid rgba(0, 242, 254, 0.3); }
.pro-icon { background: rgba(168, 85, 247, 0.1); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); }

.engine-name { font-size: 18px; font-weight: 900; letter-spacing: 1px; margin-bottom: 4px; display: flex; align-items: baseline; gap: 8px;}
.engine-name span { font-size: 11px; color: #718096; font-family: monospace; font-weight: normal; }
.engine-desc { font-size: 12px; color: #a0aec0; margin-bottom: 12px; }

.engine-status-label { font-size: 11px; font-family: monospace; font-weight: bold; letter-spacing: 0.5px; }
.engine-status-label.online { color: #10b981; }
.engine-status-label.offline { color: #f43f5e; animation: blink 2s infinite; }

.engine-action { flex-shrink: 0; }
.cyber-switch :deep(.el-switch__core) { border: 1px solid rgba(255,255,255,0.2); }
.fast-switch { --el-switch-on-color: #00f2fe; --el-switch-off-color: #334155; }
.pro-switch { --el-switch-on-color: #a855f7; --el-switch-off-color: #334155; }

:global(.cyber-toast) { background: rgba(10, 15, 20, 0.9) !important; border: 1px solid #00f2fe !important; backdrop-filter: blur(10px) !important; color: #fff !important; font-family: 'Inter', monospace !important; border-radius: 8px !important; }

/* Admin 弹窗及表单样式 */
:deep(.el-dialog.cyber-dialog) { background: rgba(15, 20, 25, 0.9); border: 1px solid rgba(0, 242, 254, 0.4); backdrop-filter: blur(30px); border-radius: 16px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8), inset 0 0 20px rgba(0, 242, 254, 0.05); }
:deep(.el-dialog__title) { color: #00f2fe; font-weight: 800; letter-spacing: 1px; font-size: 14px; }
:deep(.el-dialog__headerbtn .el-dialog__close) { color: #a0aec0; }
:deep(.el-dialog__headerbtn:hover .el-dialog__close) { color: #f43f5e; }
:deep(.el-form-item__label) { color: #a0aec0; font-size: 11px; font-family: monospace; letter-spacing: 1px; }
:deep(.el-input__wrapper), :deep(.el-input-number__increase), :deep(.el-input-number__decrease) { background: rgba(0, 0, 0, 0.5) !important; box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset !important; }
:deep(.el-input__inner) { color: #fff; font-family: monospace; }
:deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #00f2fe inset !important; }
:deep(.el-input.is-disabled .el-input__wrapper) { background: rgba(0, 0, 0, 0.8) !important; }
:deep(.el-input.is-disabled .el-input__inner) { color: #718096; }
:deep(.el-radio__label) { color: #cbd5e1; }
:deep(.el-radio.is-checked .el-radio__label) { color: #00f2fe; }

.dialog-footer { display: flex; justify-content: flex-end; gap: 15px; }
.cyber-btn-cancel { background: transparent; border: none; color: #718096; font-weight: 700; font-family: monospace; cursor: pointer; transition: 0.3s; padding: 0 15px; }
.cyber-btn-cancel:hover { color: #fff; }
.cyber-btn-solid { background: #00f2fe; border: none; border-radius: 8px; color: #000; font-weight: 800; padding: 10px 20px; font-family: 'Inter', sans-serif; cursor: pointer; transition: 0.3s; box-shadow: 0 0 15px rgba(0, 242, 254, 0.3); }
.cyber-btn-solid:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 0 25px rgba(0, 242, 254, 0.6); }
.cyber-btn-solid:disabled { background: #334155; color: #94a3b8; cursor: not-allowed; box-shadow: none; }
</style>
