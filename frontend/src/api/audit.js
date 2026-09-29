import request from '@/utils/request'

export const getAuditTables = () => request.get('/audit-logs/tables')

export const getAuditLogs = (params) => request.get('/audit-logs', { params })

export const exportAuditLogs = (params) =>
  request.get('/audit-logs/export', { params, responseType: 'blob' })