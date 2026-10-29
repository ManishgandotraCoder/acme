import { describe, expect, it } from 'vitest'
import { formatDate, formatMoney } from './format'

describe('formatMoney', () => {
  it('formats whole amounts with currency code and grouping', () => {
    expect(formatMoney(2400000, 'INR')).toBe('INR 2,400,000')
    expect(formatMoney(80000, 'GBP')).toBe('GBP 80,000')
  })

  it('rounds fractional amounts', () => {
    expect(formatMoney(1234.6, 'USD')).toBe('USD 1,235')
  })
})

describe('formatDate', () => {
  it('formats ISO dates without timezone drift', () => {
    expect(formatDate('2020-01-05')).toBe('5 Jan 2020')
  })
})
