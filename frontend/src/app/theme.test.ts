import { describe, expect, it } from 'vitest'
import { theme } from './theme'

/** WCAG 2.x relative luminance / contrast ratio. */
function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

describe('theme', () => {
  const mauve = theme.colors!.mauve!
  const shade = theme.primaryShade as { light: number; dark: number }

  it('uses the magenta-grey "mauve" palette as primary', () => {
    expect(theme.primaryColor).toBe('mauve')
    expect(mauve).toHaveLength(10)
  })

  it('keeps button text readable (WCAG AA 4.5:1) in light and dark mode', () => {
    expect(contrast('#ffffff', mauve[shade.light])).toBeGreaterThanOrEqual(4.5)
    expect(contrast('#ffffff', mauve[shade.dark])).toBeGreaterThanOrEqual(4.5)
  })

  it.each(['mauve', 'gray', 'dark'])('%s scale goes from light to dark across 10 shades', (name) => {
    const l = theme.colors![name]!.map(luminance)
    expect(l).toHaveLength(10)
    expect(l).toEqual([...l].sort((a, b) => b - a))
  })

  it('tints neutrals toward magenta so greys match the brand', () => {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(theme.colors!.gray![3].slice(i, i + 2), 16))
    expect(r).toBeGreaterThan(g) // red + blue above green = magenta cast
    expect(b).toBeGreaterThan(g)
  })

  it('keeps dimmed text readable (AA) on light and dark surfaces', () => {
    const { gray, dark } = theme.colors!
    expect(contrast(gray![6], '#ffffff')).toBeGreaterThanOrEqual(4.5)
    expect(contrast(dark![2], dark![7])).toBeGreaterThanOrEqual(4.5)
  })
})
