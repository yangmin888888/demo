const pad = (n) => String(n).padStart(2, '0')

// 形如 2026-09-29T04:36:49（不带 Z 也不带 +08:00）的时间串
const NAIVE = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/

/**
 * 把后端返回的 ISO 时间串格式化为本地时间 "YYYY-MM-DD HH:mm:ss"。
 *
 * 两个坑：
 * 1. 后端时间列统一是 aware 的 UTC（末尾带 +00:00），直接 replace('T', ' ')
 *    会把 "+00:00" 一起显示出来，而且显示的还是 UTC 而非本地时间。
 * 2. localStorage 里可能还存着本函数出现之前写入的无时区串，按 ES 规范
 *    new Date() 会把它当**本地时间**，整整差一个时区偏移。这类串一律补 Z。
 */
export function formatDateTime(value) {
  if (!value) return '-'
  const raw = String(value)
  const iso = NAIVE.test(raw) ? raw.replace(' ', 'T') + 'Z' : raw
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return raw.replace('T', ' ')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}
