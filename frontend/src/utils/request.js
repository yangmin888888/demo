import axios from 'axios'
import { ElMessage } from 'element-plus'

let onUnauthorized = null
let onForbidden = null

// request.js 若直接 import router / store 会形成循环依赖
// （store -> api -> request），改由 main.js 在启动时注入错误处理逻辑
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

export function setForbiddenHandler(handler) {
  onForbidden = handler
}

/**
 * 业务字段名 -> 中文，用于拼接 422 报错。
 * 只覆盖后端 schema 里出现过的字段，未登记的直接显示原名。
 */
const FIELD_LABELS = {
  username: '用户名',
  email: '邮箱',
  nickname: '昵称',
  password: '密码',
  page: '页码',
  size: '每页条数',
  table_name: '业务表',
  action: '操作类型',
  record_id: '记录ID',
  start_time: '开始时间',
  end_time: '结束时间',
  limit: '条数上限',
}

/**
 * pydantic v2 的 type -> 中文说明。
 * 模板函数会利用 ctx 里的约束值，把"至少 3 个字符"这类具体要求带出来，
 * 而不是笼统地说"格式不正确"。
 */
const TYPE_TEMPLATES = {
  missing: () => '不能为空',
  string_too_short: (c) => (c?.min_length != null ? `长度不足（至少 ${c.min_length} 个字符）` : '长度不足'),
  string_too_long: (c) => (c?.max_length != null ? `长度超出限制（最多 ${c.max_length} 个字符）` : '长度超出限制'),
  string_type: () => '必须是文本',
  int_type: () => '必须是整数',
  int_parsing: () => '格式不正确，应为整数',
  float_type: () => '必须是数字',
  float_parsing: () => '格式不正确，应为数字',
  bool_type: () => '必须是布尔值',
  bool_parsing: () => '格式不正确，应为布尔值',
  greater_than_equal: (c) => (c?.ge != null ? `数值过小（不能小于 ${c.ge}）` : '数值过小'),
  less_than_equal: (c) => (c?.le != null ? `数值过大（不能大于 ${c.le}）` : '数值过大'),
  greater_than: (c) => (c?.gt != null ? `数值过小（必须大于 ${c.gt}）` : '数值过小'),
  less_than: (c) => (c?.lt != null ? `数值过大（必须小于 ${c.lt}）` : '数值过大'),
  multiple_of: (c) => (c?.multiple_of != null ? `必须是 ${c.multiple_of} 的倍数` : '数值不合法'),
  email: () => '格式不是有效的邮箱地址',
  json_invalid: () => '格式不正确，应为 JSON',
}

/** 把单条 pydantic 错误转成中文说明 */
function resolveMessage(item) {
  const type = item?.type
  const raw = String(item?.msg || '').replace(/^Value error,\s*/, '')
  // value_error 承载的是业务自定义原因（如"密码至少 6 位"），比模板更具体，优先保留
  if (type === 'value_error' && raw) return raw
  const template = TYPE_TEMPLATES[type]
  if (template) return template(item?.ctx)
  return raw || '不符合要求'
}

/** FastAPI 422 的 detail 是数组，这里拆成 { field, message } 供表单定位 */
export function parseValidationErrors(detail) {
  if (!Array.isArray(detail)) return []
  return detail.map((item) => {
    const loc = Array.isArray(item?.loc) ? item.loc : []
    // loc 形如 ["body", "username"]，末段才是字段名
    const field = loc.length > 1 ? String(loc[loc.length - 1]) : String(loc[0] ?? '')
    return { field, message: resolveMessage(item), type: item?.type, loc }
  })
}

const STATUS_MESSAGES = {
  400: '请求有误',
  403: '没有访问权限',
  404: '请求的资源不存在',
  409: '数据冲突',
  422: '提交的数据未通过校验',
  429: '操作过于频繁，请稍后再试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务暂不可用',
  504: '网关超时',
}

/** 把任意形态的错误响应体转成一句可读的中文提示 */
function formatErrorMessage(status, data) {
  const detail = data?.detail
  if (typeof detail === 'string' && detail) return detail
  const errors = parseValidationErrors(detail)
  if (errors.length) {
    const first = errors[0]
    const name = FIELD_LABELS[first.field] || first.field
    const rest = errors.length > 1 ? `（另有 ${errors.length - 1} 项待修正）` : ''
    return `${name}${first.message}${rest}`
  }
  return STATUS_MESSAGES[status] || '请求失败'
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
  (response) => {
    // 二进制下载（如 CSV 导出）需要读响应头判断是否被截断，保留完整响应体
    if (response.config.responseType === 'blob') {
      return { data: response.data, headers: response.headers }
    }
    return response.data
  },
  (error) => {
    const status = error.response?.status
    const data = error.response?.data
    const message = formatErrorMessage(status, data)
    const url = error.config?.url || ''

    // /auth/me 返回 403 只可能是账号被禁用，属于会话终止而非权限不足，
    // 按路径判定比匹配后端文案更可靠。
    const sessionEnded = status === 401 || (status === 403 && url.endsWith('/auth/me'))

    if (sessionEnded) {
      // 先清持久化数据，再交给注入的处理器同步清 Pinia 状态并跳转
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      onUnauthorized?.()
    } else if (status === 403) {
      onForbidden?.(message)
    }

    // 422 附带结构化错误，方便页面把提示落到具体表单项上
    if (status === 422) {
      error.validationErrors = parseValidationErrors(data?.detail)
    }

    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default request
