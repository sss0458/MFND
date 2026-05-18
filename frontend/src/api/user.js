import axios from 'axios'
const api = axios.create({ baseURL: '/api' })

// 1. 获取列表
export const getUserList = () => {
  return api.get('/users')
}

// 2. 新增用户
export const createUser = (data) => {
  return api.post('/users', data)
}

// 3. 更新状态
export const updateUserStatus = (id, status) => {
  return api.put(`/users/${id}/status`, { status })
}

// 4. 删除用户
export const deleteUser = (id) => {
  return api.delete(`/users/${id}`)
}