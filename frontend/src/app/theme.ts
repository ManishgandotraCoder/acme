import { createTheme, Loader, Skeleton, type MantineColorsTuple } from '@mantine/core'

/**
 * Muted magenta-grey brand palette, light → dark. Shade 7 is the primary: white text on it
 * meets WCAG AA (5.5:1). All contrast claims here are asserted in theme.test.ts.
 */
const mauve: MantineColorsTuple = [
  '#f8f1f6',
  '#ece2e9',
  '#dcc6d6',
  '#cba8c1',
  '#bd8eaf',
  '#b07da3',
  '#a06c93',
  '#8a5a7e',
  '#784c6e',
  '#653f5d',
]

/** Neutrals with a faint magenta cast so borders, stripes and skeletons match the brand. */
const gray: MantineColorsTuple = [
  '#faf8f9',
  '#f3f0f2',
  '#ebe6e9',
  '#e0d9de',
  '#cfc6cc',
  '#ada2aa',
  '#72666f', // dimmed text: 5.5:1 on white (Mantine default is 3.3:1)
  '#4f454c',
  '#3a3138',
  '#251f24',
]

/** Dark-mode surfaces, same faint magenta cast. */
const dark: MantineColorsTuple = [
  '#cfc9cd',
  '#b9b2b7',
  '#9a9198', // dimmed text: 5.2:1 on the body background
  '#6c656a',
  '#463f44',
  '#3c353a',
  '#302a2e',
  '#262125', // body background
  '#201b1f',
  '#151215',
]

export const theme = createTheme({
  primaryColor: 'mauve',
  primaryShade: { light: 7, dark: 7 },
  colors: { mauve, gray, dark },
  defaultRadius: 'md',
  components: {
    Loader: Loader.extend({ defaultProps: { type: 'dots' } }),
    Skeleton: Skeleton.extend({ defaultProps: { radius: 'sm' } }),
  },
})
