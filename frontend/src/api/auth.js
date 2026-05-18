import axios from 'axios'

// 这里的 /api 会被 vite.config.js 代理转发到 http://localhost:8000
const api = axios.create({ baseURL: '/api' })

export const loginRequest = (data) => {
  return api.post('/login', data)
}

export const registerRequest = (data) => {
  return api.post('/register', data)
}

export const fetchRecoveryQuestionRequest = (username) => {
  return api.post('/password-recovery/question', { username })
}

export const resetPasswordBySecurityRequest = (data) => {
  return api.post('/password-recovery/reset', data)
}
