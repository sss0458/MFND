import axios from 'axios'
const api = axios.create({ baseURL: '/api' })

// 获取审核列表
export const getPendingTasks = () => {
  return api.get('/tasks')
}

// 提交审核结果
export const submitAudit = (data) => {
  return api.post('/audit_task', data)
}

// 单条多模态检测
export const uploadMedia = ({ text, images = [], video = null, modelType = 'fast' }) => {
  const formData = new FormData()
  formData.append('model_type', modelType)

  if (text) formData.append('text', text)
  images.forEach((image) => formData.append('images', image))
  if (video) formData.append('video', video)

  return api.post('/upload_detect', formData)
}

// 批量新闻图文检测
export const uploadBatchNews = ({ texts, batchFile = null, images = [], modelType = 'fast' }) => {
  const formData = new FormData()
  formData.append('model_type', modelType)

  if (texts) formData.append('texts', texts)
  if (batchFile) formData.append('batch_file', batchFile)
  images.forEach((image) => formData.append('images', image))

  return api.post('/upload_detect_batch', formData)
}
