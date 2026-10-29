import { createTheme, Loader, Skeleton, type MantineColorsTuple } from '@mantine/core'

/**
 * Green brand palette, light → dark. Shade 7 is the primary: white text on it meets WCAG AA
 * (5.3:1). All contrast claims here are asserted in theme.test.ts.
 */
const brand: MantineColorsTuple = [
  '#ecf8f1',
  '#d6efe1',
  '#acdec2',
  '#7fcba1',
  '#58b985',
  '#3fa872',
  '#2f9763', // chart bars: 3.7:1 on white, 4.2:1 on dark
  '#1f7a4f', // primary
  '#186642',
  '#105234',
]

/** Neutrals with a faint green cast so borders, stripes and skeletons match the brand. */
const gray: MantineColorsTuple = [
  '#f7f9f8',
  '#eff3f1',
  '#e5ebe8',
  '#d8e0dc',
  '#c4cec9',
  '#9ea9a3',
  '#647069', // dimmed text: 5.2:1 on white (Mantine default is 3.3:1)
  '#454f4a',
  '#313935',
  '#1e2421',
]

/** Dark-mode surfaces, same faint green cast. */
const dark: MantineColorsTuple = [
  '#c8cfcb',
  '#b1b9b4',
  '#919a95', // dimmed text: 5.3:1 on the body background
  '#646c68',
  '#3f4642',
  '#363c39',
  '#2a302d',
  '#212623', // body background
  '#1b1f1d',
  '#121513',
]

export const theme = createTheme({
  primaryColor: 'brand',
  primaryShade: { light: 7, dark: 7 },
  colors: { brand, gray, dark },
  defaultRadius: 'md',
  components: {
    Loader: Loader.extend({ defaultProps: { type: 'dots' } }),
    Skeleton: Skeleton.extend({ defaultProps: { radius: 'sm' } }),
  },
})
