import { describe, expect, it } from 'vitest'
import { formatValue } from './valueFormat'

describe('formatValue', () => {
  it('formats money, local currency, signed percentages and counts', () => {
    expect(formatValue(100299, 'usd')).toBe('USD 100,299')
    expect(formatValue(95000, 'local', 'EUR')).toBe('EUR 95,000')
    expect(formatValue(8.5, 'percent')).toBe('+8.5%')
    expect(formatValue(-12.25, 'percent')).toBe('-12.3%')
    expect(formatValue(3519, 'number')).toBe('3,519')
  })
})
