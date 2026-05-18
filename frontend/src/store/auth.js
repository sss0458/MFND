import { defineStore } from 'pinia'
import { loginRequest } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    role: localStorage.getItem('role') || '', // 'user' | 'auditor' | 'admin'
    username: localStorage.getItem('username') || ''
  }),
  
  actions: {
    async login(loginForm) {
      try {
        // 1. 调用 API
        const res = await loginRequest(loginForm)
        
        console.log('完整 Axios 响应:', res)
        console.log('后端返回的数据体:', res.data)
        const payload = res.data.data || res.data
        const {token , role , username} = payload
        console.log('解析出的角色(Role):' , role) 
        if (!role) {
          throw new Error('后端未返回角色信息，登录异常')
        }
        
        // 3. 保存状态到 Pinia 和 LocalStorage (防止刷新丢失)
        this.token = token
        this.role = role
        this.username = username
        
        localStorage.setItem('token', token)
        localStorage.setItem('role', role)
        localStorage.setItem('username', username)
        
        return role // 返回角色，方便页面决定跳转去哪里
      } catch (error) {
        throw error // 抛出错误给前端页面捕获
      }
    },
    
    logout() {
      this.token = ''
      this.role = ''
      this.username = ''
      localStorage.clear()
    }
  }
})