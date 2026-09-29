import request from '@/utils/request'

export const getAuditTables = () => request.get('/audit-logs/tables')

/** 表名/字段名/操作类型的中文映射，由后端统一维护，前端不再硬编码副本 */
export const getAuditLabels = () => request.get('/audit-logs/labels')

export const getAuditLogs = (params) => request.get('/audit-logs', { params })

/** 返回 { data, headers }，响应头里的截断标记需要被页面读取 */
export const exportAuditLogs = (params) =>
  request.get('/audit-logs/export', { params, responseType: 'blob' })