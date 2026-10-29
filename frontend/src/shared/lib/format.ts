const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const date = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })

export function formatMoney(amount: number, currency: string): string {
  return `${currency} ${number.format(Math.round(amount))}`
}

export function formatNumber(value: number): string {
  return number.format(value)
}

/** Formats a `YYYY-MM-DD` or ISO timestamp; dates are treated as UTC to avoid off-by-one days. */
export function formatDate(iso: string): string {
  return date.format(new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso))
}
