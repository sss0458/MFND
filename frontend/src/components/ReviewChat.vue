<template>
  <section class="review-chat-panel">
    <div class="chat-header">
      <div>
        <div class="chat-title">审核沟通信道</div>
        <div class="chat-subtitle">TASK #{{ taskId }} · {{ roleLabel }}</div>
        <div class="presence-row">
          <span class="presence-pill" :class="{ online: selfPresence.online }">
            <span class="presence-dot"></span>
            我{{ selfPresence.online ? '在线' : '同步中' }}
          </span>
          <span class="presence-pill" :class="{ online: counterpartPresence.online }">
            <span class="presence-dot"></span>
            {{ counterpartLabel }}{{ counterpartPresence.online ? '在线' : '离线' }}
          </span>
        </div>
      </div>
      <button class="icon-btn" type="button" title="刷新消息和在线状态" @click="refreshRealtimeState">
        <el-icon :class="{ 'is-spinning': isFetching }"><Refresh /></el-icon>
      </button>
    </div>

    <div ref="messageListRef" class="message-list">
      <div v-if="messages.length === 0" class="empty-chat">
        这里会显示用户与审核员围绕该任务的沟通记录。
      </div>
      <div
        v-for="message in messages"
        :key="message.id"
        class="message-row"
        :class="{ mine: message.sender_role === role }"
      >
        <div class="message-bubble">
          <div class="message-meta">
            <span>{{ message.sender_name }}</span>
            <time>{{ formatTime(message.create_time) }}</time>
          </div>
          <div class="message-content">{{ message.content }}</div>
        </div>
      </div>
    </div>

    <div class="chat-input-row">
      <textarea
        v-model="draft"
        class="chat-input"
        rows="2"
        maxlength="1000"
        placeholder="输入你对审核结果的疑问或补充说明..."
        @keydown.enter.exact.prevent="sendMessage"
      />
      <button class="send-btn" type="button" :disabled="!draft.trim() || isSending" @click="sendMessage">
        <el-icon><Position /></el-icon>
        <span>{{ isSending ? '发送中' : '发送' }}</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Position, Refresh } from '@element-plus/icons-vue'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

const props = defineProps({
  taskId: { type: [Number, String], required: true },
  role: { type: String, required: true },
  senderName: { type: String, default: '' },
})

const messages = ref([])
const draft = ref('')
const isFetching = ref(false)
const isSending = ref(false)
const messageListRef = ref(null)
const presence = ref({
  user: { online: false, name: '用户', last_seen: null },
  auditor: { online: false, name: '审核员', last_seen: null },
})
let pollTimer = null
let heartbeatTimer = null

const roleLabel = computed(() => (props.role === 'auditor' ? '审核员端' : '用户端'))
const counterpartRole = computed(() => (props.role === 'auditor' ? 'user' : 'auditor'))
const counterpartLabel = computed(() => (props.role === 'auditor' ? '用户' : '审核员'))
const selfPresence = computed(() => presence.value[props.role] || { online: false })
const counterpartPresence = computed(() => presence.value[counterpartRole.value] || { online: false })

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const fetchMessages = async () => {
  if (!props.taskId) return
  isFetching.value = true
  try {
    const res = await api.get(`/tasks/${props.taskId}/messages`)
    if (res.data?.code === 200) {
      messages.value = res.data.data || []
      await scrollToBottom()
    }
  } catch (error) {
    console.error('同步审核沟通消息失败', error)
  } finally {
    isFetching.value = false
  }
}

const fetchPresence = async () => {
  if (!props.taskId) return
  try {
    const res = await api.get(`/tasks/${props.taskId}/presence`)
    if (res.data?.code === 200) {
      presence.value = res.data.data
    }
  } catch (error) {
    console.error('同步在线状态失败', error)
  }
}

const sendPresence = async () => {
  if (!props.taskId) return
  try {
    const res = await api.put(`/tasks/${props.taskId}/presence`, {
      role: props.role,
      name: props.senderName,
    })
    if (res.data?.code === 200) {
      presence.value = res.data.data
    }
  } catch (error) {
    console.error('更新在线状态失败', error)
  }
}

const sendMessage = async () => {
  const content = draft.value.trim()
  if (!content || isSending.value) return

  isSending.value = true
  try {
    const res = await api.post(`/tasks/${props.taskId}/messages`, {
      sender_role: props.role,
      sender_name: props.senderName,
      content,
    })
    if (res.data?.code === 200) {
      draft.value = ''
      messages.value.push(res.data.data)
      await scrollToBottom()
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '消息发送失败')
  } finally {
    isSending.value = false
  }
}

const refreshRealtimeState = async () => {
  await Promise.all([fetchMessages(), fetchPresence()])
}

const formatTime = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const startPolling = () => {
  window.clearInterval(pollTimer)
  pollTimer = window.setInterval(refreshRealtimeState, 4000)
}

const startHeartbeat = () => {
  window.clearInterval(heartbeatTimer)
  heartbeatTimer = window.setInterval(sendPresence, 8000)
}

watch(
  () => props.taskId,
  async () => {
    messages.value = []
    draft.value = ''
    await sendPresence()
    await refreshRealtimeState()
    startPolling()
    startHeartbeat()
  },
)

onMounted(async () => {
  await sendPresence()
  await refreshRealtimeState()
  startPolling()
  startHeartbeat()
})

onBeforeUnmount(() => {
  window.clearInterval(pollTimer)
  window.clearInterval(heartbeatTimer)
})
</script>

<style scoped>
.review-chat-panel {
  display: flex;
  flex-direction: column;
  min-height: 280px;
  border: 1px solid rgba(0, 242, 254, 0.18);
  border-radius: 12px;
  background: rgba(3, 8, 12, 0.62);
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(0, 242, 254, 0.14);
}

.chat-title {
  color: #00f2fe;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1px;
}

.chat-subtitle {
  margin-top: 4px;
  color: #718096;
  font-size: 10px;
  letter-spacing: 1px;
}

.presence-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 9px;
}

.presence-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(148, 163, 184, 0.08);
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
}

.presence-pill.online {
  border-color: rgba(16, 185, 129, 0.34);
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
}

.presence-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #64748b;
  box-shadow: 0 0 0 2px rgba(100, 116, 139, 0.12);
}

.presence-pill.online .presence-dot {
  background: #10b981;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.72);
}

.icon-btn {
  width: 34px;
  height: 34px;
  border: 1px solid rgba(0, 242, 254, 0.28);
  border-radius: 8px;
  background: rgba(0, 242, 254, 0.06);
  color: #00f2fe;
  cursor: pointer;
  transition: 0.25s;
}

.icon-btn:hover {
  background: rgba(0, 242, 254, 0.14);
}

.message-list {
  flex: 1;
  min-height: 150px;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-list::-webkit-scrollbar,
.chat-input::-webkit-scrollbar {
  width: 4px;
}

.message-list::-webkit-scrollbar-thumb,
.chat-input::-webkit-scrollbar-thumb {
  background: rgba(0, 242, 254, 0.3);
  border-radius: 2px;
}

.empty-chat {
  margin: auto;
  color: #718096;
  font-size: 12px;
  text-align: center;
  line-height: 1.6;
}

.message-row {
  display: flex;
  justify-content: flex-start;
}

.message-row.mine {
  justify-content: flex-end;
}

.message-bubble {
  max-width: min(84%, 520px);
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.message-row.mine .message-bubble {
  background: rgba(0, 242, 254, 0.12);
  border-color: rgba(0, 242, 254, 0.32);
}

.message-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 10px;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  color: #f8fafc;
  font-size: 13px;
  line-height: 1.6;
}

.chat-input-row {
  display: grid;
  grid-template-columns: 1fr 82px;
  gap: 10px;
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.chat-input {
  resize: none;
  min-width: 0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.36);
  color: #fff;
  padding: 10px 12px;
  outline: none;
  font-size: 12px;
  line-height: 1.5;
  font-family: inherit;
}

.chat-input:focus {
  border-color: rgba(0, 242, 254, 0.65);
  box-shadow: 0 0 0 2px rgba(0, 242, 254, 0.08);
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: none;
  border-radius: 8px;
  background: #00f2fe;
  color: #001014;
  font-weight: 800;
  cursor: pointer;
  transition: 0.25s;
}

.send-btn:hover:not(:disabled) {
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.36);
}

.send-btn:disabled {
  background: #334155;
  color: #94a3b8;
  cursor: not-allowed;
}

.is-spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
