/**
 * 客户端侧的 JWT 解析工具。
 *
 * 只用于"快速判断 token 是否已过期"，不做签名校验——签名校验只有服务端能做。
 * 真正的有效性确认仍然依赖调用 /auth/me。
 */

/** base64url 解码为 UTF-8 字符串 */
function decodeBase64Url(segment) {
  const padded = segment.replace(/-/g, '+').replace(/_/g, '/')
  const binary = atob(padded)
  // 逐字节转成 %XX 再交给 decodeURIComponent，正确处理中文等非 ASCII 字符
  const percent = Array.from(binary, (c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0')).join('')
  return decodeURIComponent(percent)
}

/** 解析 JWT 载荷，失败返回 null。仅供展示与过期判断，不可用于鉴权。 */
export function decodeJwt(token) {
  if (!token || typeof token !== 'string') return null
  const parts = token.split('.')
  if (parts.length !== 3) return null
  try {
    return JSON.parse(decodeBase64Url(parts[1]))
  } catch {
    return null
  }
}

/**
 * token 是否已过期。
 * skewSeconds 给时钟误差留出余量，避免"服务端还没过期、前端却认为过期"的边界抖动。
 */
export function isTokenExpired(token, skewSeconds = 10) {
  const payload = decodeJwt(token)
  if (!payload?.exp) return true
  return payload.exp * 1000 <= Date.now() + skewSeconds * 1000
}
