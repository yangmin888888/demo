import axios from 'axios'
import { ElMessage } from 'element-plus'

let onUnauthorized = null

// request.js 若直接 import router / store 会形成循环依赖
// （store -> api -> request），改由 main.js 在启动时注入 401 后的处理逻辑
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error.response?.data?.detail
    if (error.response?.status === 401) {
      // 先清持久化数据，再交给注入的处理器同步清 Pinia 状态并跳转
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      onUnauthorized?.()
    }
    ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
    return Promise.reject(error)
  },
)

export default request
