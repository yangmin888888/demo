import { defineStore } from 'pinia'
import { login as loginApi, fetchMe, logoutApi } from '@/api/auth'
import { isTokenExpired } from '@/utils/token'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null'),
    // 本次会话是否已向后端确认过登录态，防止路由守卫反复校验
    sessionChecked: false,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    isSuperuser: (state) => !!state.userInfo?.is_superuser,
    displayName: (state) => state.userInfo?.nickname || state.userInfo?.username || '',
  },
  actions: {
    async login(form) {
      const data = await loginApi(form)
      this.token = data.access_token
      localStorage.setItem('token', this.token)
      await this.loadUserInfo()
      this.sessionChecked = true
    },
    async loadUserInfo() {
      const user = await fetchMe()
      this.userInfo = user
      localStorage.setItem('userInfo', JSON.stringify(user))
    },
    /**
     * 仅清除本地登录态，不通知后端。
     * 用于 token 已经被后端判为失效的场景（401），此时再调登出接口没有意义。
     */
    clearSession() {
      this.token = ''
      this.userInfo = null
      this.sessionChecked = true
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    },
    /** 主动登出：先通知后端把 token 加入撤销名单，再清本地 */
    async logout() {
      try {
        await logoutApi()
      } catch {
        // 后端不可达时也要让用户能登出本地，不能因此卡住
      } finally {
        this.clearSession()
      }
    },
    /**
     * 页面刷新后恢复登录态。
     *
     * localStorage 里的 token 可能早已过期或已被撤销，直接拿来用会让用户
     * 看到陈旧的用户信息，直到下一次接口调用才暴露问题。这里先做一次
     * 客户端过期判断（无需往返），再向 /auth/me 确认一次真实有效性。
     */
    async restoreSession() {
      if (this.sessionChecked) return
      if (!this.token) {
        this.sessionChecked = true
        return
      }
      if (isTokenExpired(this.token)) {
        this.clearSession()
        return
      }
      try {
        await this.loadUserInfo()
      } catch {
        // 401/403 交给全局拦截器提示，这里只负责把本地状态收敛掉
        this.clearSession()
      } finally {
        this.sessionChecked = true
      }
    },
  },
})
