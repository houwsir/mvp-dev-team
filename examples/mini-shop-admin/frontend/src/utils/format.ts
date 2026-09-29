export function formatMoney(value: string | number) {
  const amount = Number(value)
  return Number.isFinite(amount) ? `¥${amount.toFixed(2)}` : '¥0.00'
}

export function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  const parts = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(date)
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}:${map.second}`
}
