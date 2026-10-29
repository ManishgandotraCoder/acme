import { formatMoney, formatNumber } from '@/shared/lib/format'
import type { Column } from './types'

/** Formats a table or chart value as the backend's column format says. */
export function formatValue(value: number, format: Column['format'], currency?: string): string {
  switch (format) {
    case 'usd':
      return formatMoney(value, 'USD')
    case 'local':
      return formatMoney(value, currency ?? '')
    case 'percent':
      return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`
    default:
      return formatNumber(value)
  }
}
