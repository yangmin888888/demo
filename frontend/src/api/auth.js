import request from '@/utils/request'

export const login = (data) => request.post('/auth/login', data)

export const fetchMe = () => request.get('/auth/me')

/** 登出：通知后端把当前 token 加入撤销名单，使其立即失效 */
export const logoutApi = () => request.post('/auth/logout')
