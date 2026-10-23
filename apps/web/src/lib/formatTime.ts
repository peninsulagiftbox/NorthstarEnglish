const beijingTime = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
});
/** JDBC DATETIME values arrive without an offset; the API/database contract is UTC. */
export function utcTimestamp(value: string): string {
  return /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`;
}
export function formatBeijingTime(value: string): string {
  const date = new Date(utcTimestamp(value));
  if (!Number.isFinite(date.getTime())) return '时间未知';
  const parts = Object.fromEntries(beijingTime.formatToParts(date).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
}
