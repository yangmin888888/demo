import { defineStore } from 'pinia'
import { login as loginApi, fetchMe } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null'),
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
    },
    async loadUserInfo() {
      const user = await fetchMe()
      this.userInfo = user
      localStorage.setItem('userInfo', JSON.stringify(user))
    },
    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    },
  },
})
