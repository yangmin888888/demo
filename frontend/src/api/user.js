import request from '@/utils/request'

export const getUserList = (params) => request.get('/users', { params })

export const createUser = (data) => request.post('/users', data)

export const updateUser = (id, data) => request.put(`/users/${id}`, data)

export const deleteUser = (id) => request.delete(`/users/${id}`)
