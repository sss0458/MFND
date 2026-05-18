<template>
  <div class="user-manage-container">
    
    <div class="cyber-toolbar">
      <div class="toolbar-left">
        <div class="module-title">
          <span class="indicator"></span>
          ACCESS CONTROL // 权限与身份链路管理
        </div>
      </div>
      <div class="toolbar-right">
        <el-input
          v-model="searchQuery"
          placeholder="检索节点 / SYSTEM ID..."
          clearable
          class="cyber-search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <button class="cyber-action-btn primary-glow" @click="openDialog('add')">
          <el-icon class="btn-icon"><Plus /></el-icon>
          <span>注册新节点</span>
        </button>
      </div>
    </div>

    <div class="cyber-table-wrapper">
      <el-table 
        :data="filteredUsers" 
        style="width: 100%" 
        v-loading="loading"
        class="cyber-table"
        element-loading-background="rgba(0, 0, 0, 0.7)"
        element-loading-text="SYNCING DATA..."
      >
        <el-table-column prop="id" label="ID" width="80" align="center" sortable>
          <template #default="{ row }">
            <span class="cyber-id">#{{ row.id.toString().padStart(4, '0') }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="username" label="身份标识 (USERNAME)" min-width="140">
          <template #default="{ row }">
            <span class="cyber-username">{{ row.username }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="nickname" label="昵称 (NICKNAME)" min-width="120" align="center">
          <template #default="{ row }">
            <span class="cyber-nickname">{{ row.nickname || '未设定 (UNSET)' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="email" label="邮箱 (EMAIL)" min-width="160" align="center">
          <template #default="{ row }">
            <span class="cyber-email">{{ row.email || '未绑定 (UNLINKED)' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="gender" label="性别 (GENDER)" width="140" align="center">
          <template #default="{ row }">
            <div class="cyber-badge" :class="getGenderClass(row.gender)">
              {{ formatGender(row.gender) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="age" label="年龄 (AGE)" width="100" align="center">
          <template #default="{ row }">
            <span class="cyber-age">{{ row.age ? row.age + ' CYCLE' : 'CLASSIFIED' }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="role" label="权限等级 (CLEARANCE)" width="160" align="center">
          <template #default="{ row }">
            <div class="cyber-badge" :class="row.role">
              {{ formatRole(row.role) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="createTime" label="添加时间 (TIMESTAMP)" width="180" align="center">
          <template #default="{ row }">
            <span class="cyber-time">{{ row.createTime || '2024-XX-XX 00:00:00' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="节点状态 (STATUS)" width="120" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              inline-prompt
              active-text="ON"
              inactive-text="OFF"
              class="cyber-switch"
              @change="handleStatusChange(row)"
            />
          </template>
        </el-table-column>

        <el-table-column label="编辑 (EDIT)" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="修改权限配置" placement="top" effect="dark">
                <button class="icon-btn edit-btn" @click="openDialog('edit', row)">
                  <el-icon><Edit /></el-icon>
                </button>
              </el-tooltip>
              <el-tooltip content="物理擦除节点" placement="top" effect="dark">
                <button class="icon-btn delete-btn" @click="handleDelete(row)">
                  <el-icon><Delete /></el-icon>
                </button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        
        <template #empty>
          <div class="empty-state">
            <div class="empty-icon"></div>
            <p>NO IDENTITIES FOUND / 无匹配节点</p>
          </div>
        </template>
      </el-table>
    </div>

    <div class="cyber-pagination">
      <el-pagination 
        background 
        layout="prev, pager, next" 
        :total="50" 
        class="custom-pagination"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? 'INITIALIZE NEW NODE // 新增用户' : 'CONFIGURE NODE // 编辑权限'"
      width="450px"
      @close="resetForm"
      class="cyber-dialog"
      destroy-on-close
    >
      <el-form ref="userFormRef" :model="formData" :rules="rules" label-position="top" class="cyber-form-modal">
        <el-form-item label="身份标识 (USERNAME)" prop="username">
          <el-input v-model="formData.username" placeholder="INPUT SYSTEM ID" class="cyber-input-modal" />
        </el-form-item>
        
        <el-form-item label="访问密钥 (PASSWORD)" prop="password" v-if="dialogType === 'add'">
          <el-input 
            v-model="formData.password" 
            type="password" 
            show-password 
            placeholder="SET ACCESS KEY" 
            class="cyber-input-modal"
          />
        </el-form-item>

        <el-form-item label="密保问题 (SECURITY QUESTION)" prop="security_question" v-if="dialogType === 'add'">
          <el-input
            v-model="formData.security_question"
            placeholder="例如：你的小学名称？"
            class="cyber-input-modal"
          />
        </el-form-item>

        <el-form-item label="密保答案 (SECURITY ANSWER)" prop="security_answer" v-if="dialogType === 'add'">
          <el-input
            v-model="formData.security_answer"
            placeholder="输入密保答案"
            class="cyber-input-modal"
          />
        </el-form-item>
        
        <el-form-item label="授予权限 (CLEARANCE LEVEL)" prop="role">
          <el-select v-model="formData.role" placeholder="SELECT LEVEL" class="cyber-select-modal" popper-class="cyber-popper">
            <el-option label="Level 1: 普通用户 (User)" value="user" />
            <el-option label="Level 2: 审核员 (Auditor)" value="auditor" />
            <el-option label="Level 3: 管理员 (Admin)" value="admin" />
          </el-select>
        </el-form-item>

        <el-form-item label="备注追踪 (TRACE NOTE)">
          <el-input v-model="formData.note" type="textarea" :rows="2" class="cyber-input-modal" placeholder="OPTIONAL DESC..." />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="cyber-dialog-footer">
          <button class="cyber-btn-text" @click="dialogVisible = false">ABORT / 取消</button>
          <button class="cyber-btn-solid" @click="submitForm">EXECUTE / 确认提交</button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Search, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// API
import { getUserList, createUser, updateUserStatus, deleteUser } from '@/api/user'

const userList = ref([]) 
const loading = ref(false)
const searchQuery = ref('')
const dialogVisible = ref(false)
const dialogType = ref('add') 
const userFormRef = ref(null)

const formData = reactive({
  id: null,
  username: '',
  password: '',
  security_question: '',
  security_answer: '',
  role: 'user',
  note: ''
})

const rules = {
  username: [{ required: true, message: 'REQ: SYSTEM ID', trigger: 'blur' }],
  password: [{ required: true, message: 'REQ: ACCESS KEY', trigger: 'blur' }],
  security_question: [{ required: true, message: 'REQ: SECURITY QUESTION', trigger: 'blur' }],
  security_answer: [{ required: true, message: 'REQ: SECURITY ANSWER', trigger: 'blur' }],
  role: [{ required: true, message: 'REQ: CLEARANCE LEVEL', trigger: 'change' }]
}

const filteredUsers = computed(() => {
  if (!searchQuery.value) return userList.value
  return userList.value.filter(user => 
    user.username.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await getUserList()
    // 假设你的后端接口返回的数据中已经包含了 nickname, email, gender, age
    userList.value = res.data
  } catch (error) {
    ElMessage.error({ message: 'DATA SYNC FAILED', customClass: 'cyber-toast' })
  } finally {
    loading.value = false
  }
}

onMounted(() => { fetchUsers() })

const handleStatusChange = async (row) => {
  try {
    await updateUserStatus(row.id, row.status)
    ElMessage.success({ message: `NODE [${row.username}] STATUS UPDATED`, customClass: 'cyber-toast' })
  } catch (error) {
    row.status = row.status === 1 ? 0 : 1
    ElMessage.error({ message: 'OPERATION REJECTED', customClass: 'cyber-toast' })
  }
}

const submitForm = async () => {
  if (!userFormRef.value) return
  await userFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (dialogType.value === 'add') {
          await createUser(formData)
          ElMessage.success({ message: 'NEW NODE INITIALIZED', customClass: 'cyber-toast' })
        } else {
          ElMessage.info({ message: 'EDIT API STANDBY', customClass: 'cyber-toast' })
        }
        dialogVisible.value = false
        fetchUsers() 
      } catch (error) {
        ElMessage.error({ message: error.response?.data?.detail || 'EXECUTION FAILED', customClass: 'cyber-toast' })
      }
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `WARNING: ERASING NODE "${row.username}". THIS ACTION IS IRREVERSIBLE.`,
    'SYSTEM ALERT',
    { 
      confirmButtonText: 'CONFIRM ERASE', 
      cancelButtonText: 'ABORT', 
      type: 'warning',
      customClass: 'cyber-msg-box'
    }
  ).then(async () => {
    try {
      await deleteUser(row.id)
      ElMessage.success({ message: 'NODE ERASED FROM MATRIX', customClass: 'cyber-toast' })
      fetchUsers()
    } catch (error) {
      ElMessage.error({ message: 'ERASE FAILED', customClass: 'cyber-toast' })
    }
  }).catch(() => {})
}

const formatRole = (role) => {
  const map = { admin: 'ADMIN (LV.3)', auditor: 'AUDITOR (LV.2)', user: 'USER (LV.1)' }
  return map[role] || role
}

// 👇 新增：性别格式化方法
const formatGender = (val) => {
  if (val === 1) return 'MALE / 男'
  if (val === 2) return 'FEMALE / 女'
  return 'CLASSIFIED'
}

// 👇 新增：性别样式分配方法
const getGenderClass = (val) => {
  if (val === 1) return 'male'
  if (val === 2) return 'female'
  return 'unknown'
}

const openDialog = (type, row = null) => {
  dialogType.value = type
  dialogVisible.value = true
  if (type === 'edit' && row) {
    Object.assign(formData, row)
  } else {
    formData.id = null
    formData.username = ''
    formData.password = ''
    formData.security_question = ''
    formData.security_answer = ''
    formData.role = 'user'
    formData.note = ''
  }
}

const resetForm = () => {
  if (userFormRef.value) userFormRef.value.resetFields()
  formData.security_question = ''
  formData.security_answer = ''
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

.user-manage-container { padding: 0; font-family: 'Inter', sans-serif; height: 100%; display: flex; flex-direction: column; }

/* 顶部工具栏 */
.cyber-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.module-title { font-size: 14px; color: #a0aec0; font-weight: 700; letter-spacing: 2px; display: flex; align-items: center; gap: 10px; }
.indicator { width: 8px; height: 8px; background: #00f2fe; border-radius: 50%; box-shadow: 0 0 10px #00f2fe; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

.toolbar-right { display: flex; gap: 15px; align-items: center; }

/* 赛博输入框 */
.cyber-search-input { width: 280px; }
.cyber-search-input :deep(.el-input__wrapper) { background: rgba(0,0,0,0.4); box-shadow: 0 0 0 1px rgba(255,255,255,0.1) inset; border-radius: 8px; transition: 0.3s; }
.cyber-search-input :deep(.el-input__wrapper.is-focus) { background: rgba(0, 242, 254, 0.05); box-shadow: 0 0 0 1px #00f2fe inset, 0 0 15px rgba(0, 242, 254, 0.2); }
.cyber-search-input :deep(.el-input__inner) { color: #fff; font-family: monospace; letter-spacing: 1px; height: 38px; }

/* 发光按钮 */
.cyber-action-btn { display: flex; align-items: center; gap: 8px; padding: 0 20px; height: 38px; background: rgba(0, 242, 254, 0.1); border: 1px solid #00f2fe; border-radius: 8px; color: #00f2fe; font-weight: 700; font-family: 'Inter', sans-serif; cursor: pointer; transition: 0.3s; letter-spacing: 1px; }
.cyber-action-btn:hover { background: #00f2fe; color: #000; box-shadow: 0 0 20px rgba(0, 242, 254, 0.4); transform: translateY(-2px); }

/* --- 核心：全息数据表 --- */
.cyber-table-wrapper { flex: 1; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; overflow: hidden; padding: 1px; }

.cyber-table { --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: rgba(10, 15, 20, 0.8); --el-table-border-color: rgba(255,255,255,0.05); --el-table-row-hover-bg-color: rgba(0, 242, 254, 0.05); background-color: transparent; color: #e2e8f0; }
.cyber-table :deep(th.el-table__cell) { border-bottom: 1px solid rgba(0,242,254,0.2); color: #00f2fe; font-weight: 800; letter-spacing: 1px; font-size: 11px; }
.cyber-table :deep(td.el-table__cell) { border-bottom: 1px dashed rgba(255,255,255,0.05); padding: 12px 0; }
.cyber-table :deep(.el-table__inner-wrapper::before) { display: none; /* 去除底部白线 */ }

/* 表格内元素美化 */
.cyber-id { font-family: monospace; color: #718096; }
.cyber-username { font-weight: 700; font-size: 14px; letter-spacing: 1px; }
.cyber-time { font-family: monospace; font-size: 12px; color: #a0aec0; }

/* 👇 新增：特工代号、邮箱、年龄文字样式 */
.cyber-nickname { color: #e2e8f0; font-weight: 500; }
.cyber-email { color: #94a3b8; font-family: monospace; font-size: 12px; }
.cyber-age { color: #00f2fe; font-family: monospace; font-weight: bold; }

/* 赛博徽章（合并原有Role和新增的Gender） */
.cyber-badge { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 10px; font-weight: 900; letter-spacing: 1px; font-family: monospace; border: 1px solid; }

/* Role Colors */
.cyber-badge.admin { color: #f43f5e; border-color: rgba(244, 63, 94, 0.5); background: rgba(244, 63, 94, 0.1); box-shadow: 0 0 10px rgba(244, 63, 94, 0.2); }
.cyber-badge.auditor { color: #f59e0b; border-color: rgba(245, 158, 11, 0.5); background: rgba(245, 158, 11, 0.1); box-shadow: 0 0 10px rgba(245, 158, 11, 0.2); }
.cyber-badge.user { color: #00f2fe; border-color: rgba(0, 242, 254, 0.5); background: rgba(0, 242, 254, 0.1); box-shadow: 0 0 10px rgba(0, 242, 254, 0.2); }

/* 👇 新增：Gender Colors */
.cyber-badge.male { color: #3b82f6; border-color: rgba(59, 130, 246, 0.5); background: rgba(59, 130, 246, 0.1); box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);}
.cyber-badge.female { color: #ec4899; border-color: rgba(236, 72, 153, 0.5); background: rgba(236, 72, 153, 0.1); box-shadow: 0 0 10px rgba(236, 72, 153, 0.2);}
.cyber-badge.unknown { color: #94a3b8; border-color: rgba(148, 163, 184, 0.5); background: rgba(148, 163, 184, 0.1); }

/* 开关定制 */
.cyber-switch { --el-switch-on-color: #00f2fe; --el-switch-off-color: #334155; }
.cyber-switch :deep(.el-switch__core) { border: 1px solid rgba(255,255,255,0.1); }

/* 操作按钮 */
.action-buttons { display: flex; gap: 10px; justify-content: center; }
.icon-btn { width: 32px; height: 32px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.4); color: #a0aec0; cursor: pointer; transition: 0.3s; display: flex; align-items: center; justify-content: center; }
.edit-btn:hover { border-color: #00f2fe; color: #00f2fe; background: rgba(0, 242, 254, 0.1); box-shadow: 0 0 10px rgba(0, 242, 254, 0.2); }
.delete-btn:hover { border-color: #f43f5e; color: #f43f5e; background: rgba(244, 63, 94, 0.1); box-shadow: 0 0 10px rgba(244, 63, 94, 0.2); }

/* 翻页器定制 */
.cyber-pagination { margin-top: 20px; display: flex; justify-content: flex-end; }
.custom-pagination { --el-pagination-bg-color: rgba(0,0,0,0.4); --el-pagination-text-color: #a0aec0; --el-pagination-hover-color: #00f2fe; --el-pagination-button-disabled-bg-color: transparent; }
.custom-pagination :deep(.el-pager li) { border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; background: transparent; }
.custom-pagination :deep(.el-pager li.is-active) { background: #00f2fe; color: #000; border-color: #00f2fe; box-shadow: 0 0 10px rgba(0,242,254,0.4); }

.empty-state { padding: 40px; color: #4a5568; font-family: monospace; letter-spacing: 2px; }

/* --- 拟态弹窗全局定制 --- */
:global(.cyber-dialog) { background: rgba(15, 20, 25, 0.85) !important; backdrop-filter: blur(30px) !important; border: 1px solid rgba(0, 242, 254, 0.3) !important; border-radius: 16px !important; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8), inset 0 0 20px rgba(0, 242, 254, 0.05) !important; }
:global(.cyber-dialog .el-dialog__title) { color: #00f2fe !important; font-weight: 800 !important; font-family: 'Inter', sans-serif !important; letter-spacing: 1px !important; font-size: 14px !important; }
:global(.cyber-dialog .el-dialog__header) { border-bottom: 1px solid rgba(0,242,254,0.1) !important; margin-right: 0 !important; padding-bottom: 15px !important; }
:global(.cyber-dialog .el-dialog__body) { padding: 25px 20px !important; }

/* 弹窗表单定制 */
.cyber-form-modal :deep(.el-form-item__label) { color: #a0aec0; font-size: 11px; font-family: monospace; letter-spacing: 1px; padding-bottom: 4px; }
.cyber-input-modal :deep(.el-input__wrapper), .cyber-input-modal :deep(.el-textarea__inner) { background: rgba(0,0,0,0.5); box-shadow: 0 0 0 1px rgba(255,255,255,0.1) inset; color: #fff; border-radius: 8px; font-family: monospace; }
.cyber-input-modal :deep(.el-input__wrapper.is-focus), .cyber-input-modal :deep(.el-textarea__inner:focus) { box-shadow: 0 0 0 1px #00f2fe inset !important; background: rgba(0, 242, 254, 0.05); }

.cyber-select-modal :deep(.el-input__wrapper) { background: rgba(0,0,0,0.5); box-shadow: 0 0 0 1px rgba(255,255,255,0.1) inset; border-radius: 8px; }
.cyber-select-modal :deep(.el-input__inner) { color: #fff; font-family: monospace; }

/* 下拉菜单弹出框修饰 */
:global(.cyber-popper) { background: rgba(15, 20, 25, 0.95) !important; border: 1px solid rgba(0, 242, 254, 0.3) !important; backdrop-filter: blur(10px); }
:global(.cyber-popper .el-select-dropdown__item) { color: #a0aec0; font-family: monospace; }
:global(.cyber-popper .el-select-dropdown__item.hover), :global(.cyber-popper .el-select-dropdown__item:hover) { background-color: rgba(0, 242, 254, 0.1); color: #00f2fe; }

/* 弹窗底部按钮 */
.cyber-dialog-footer { display: flex; justify-content: flex-end; gap: 15px; }
.cyber-btn-text { background: transparent; border: none; color: #718096; font-weight: 700; font-family: monospace; cursor: pointer; transition: 0.3s; }
.cyber-btn-text:hover { color: #fff; }
.cyber-btn-solid { background: #00f2fe; border: none; border-radius: 8px; color: #000; font-weight: 800; padding: 10px 20px; font-family: 'Inter', sans-serif; cursor: pointer; transition: 0.3s; box-shadow: 0 0 15px rgba(0, 242, 254, 0.3); }
.cyber-btn-solid:hover { transform: translateY(-2px); box-shadow: 0 0 25px rgba(0, 242, 254, 0.6); }

/* 全局覆盖消息确认框 (Delete Warning) */
:global(.cyber-msg-box) { background: rgba(15, 20, 25, 0.9) !important; border: 1px solid #f43f5e !important; backdrop-filter: blur(20px) !important; }
:global(.cyber-msg-box .el-message-box__title) { color: #f43f5e !important; font-family: monospace !important; font-weight: bold; }
:global(.cyber-msg-box .el-message-box__message) { color: #e2e8f0 !important; }
:global(.cyber-msg-box .el-button--primary) { background: #f43f5e !important; border-color: #f43f5e !important; color: white !important; }
</style>
