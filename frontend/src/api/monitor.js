import axios from 'axios'
const api = axios.create({ baseURL: '/api' })

export const getSystemStats = () => {
  return api.get('/monitor_stats')
}