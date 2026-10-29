import { BarChart, DonutChart, LineChart } from '@mantine/charts'
import { Box, Group, Paper, Skeleton, Stack, Text, Title } from '@mantine/core'
import { formatMoney, formatNumber } from '@/shared/lib/format'
import type { DepartmentStats, LevelStats, SalaryBand, SalaryTrend } from './types'
import './charts.css'

const BRAND = 'brand.6' // single-series charts: one hue, no legend (the title names it)
const CATEGORICAL = ['--chart-cat-1', '--chart-cat-2', '--chart-cat-3', '--chart-cat-4', '--chart-cat-5'].map(
  (name) => `var(${name})`,
)
const usd = (v: number) => formatMoney(v, 'USD')
const pct = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`
const monthLabel = new Intl.DateTimeFormat('en-GB', { month: 'short', year: '2-digit', timeZone: 'UTC' })

/** A titled chart card; the figure's accessible name is its title. */
export function Figure({
  title,
  caption,
  loading,
  children,
}: {
  title: string
  caption?: string
  loading?: boolean
  children: React.ReactNode
}) {
  return (
    <Paper component="figure" aria-label={title} withBorder p="md" m={0}>
      <Title order={4}>{title}</Title>
      {caption && (
        <Text size="sm" c="dimmed" mb="sm">
          {caption}
        </Text>
      )}
      {loading ? <Skeleton h={200} /> : children}
    </Paper>
  )
}

export function SalaryBandsChart({ bands }: { bands?: SalaryBand[] }) {
  return (
    <Figure title="Employees by salary band (USD)" caption="Annual salary in USD at fixed FX rates." loading={!bands}>
      {bands && (
        <BarChart
          h={220}
          data={bands}
          dataKey="label"
          series={[{ name: 'headcount', label: 'Employees', color: BRAND }]}
          valueFormatter={formatNumber}
          gridAxis="y"
          barProps={{ radius: [4, 4, 0, 0] }}
          maxBarWidth={48}
        />
      )}
    </Figure>
  )
}

/** Five largest departments + "Other"; more slices than that can't be told apart. */
export function HeadcountDonut({ departments }: { departments?: DepartmentStats[] }) {
  const ranked = [...(departments ?? [])].sort((a, b) => b.headcount - a.headcount)
  const total = ranked.reduce((sum, d) => sum + d.headcount, 0)
  const rest = ranked.slice(CATEGORICAL.length)
  const slices = [
    ...ranked.slice(0, CATEGORICAL.length).map((d, i) => ({ name: d.department, value: d.headcount, color: CATEGORICAL[i] })),
    ...(rest.length
      ? [{ name: 'Other', value: rest.reduce((sum, d) => sum + d.headcount, 0), color: 'var(--chart-other)' }]
      : []),
  ]
  return (
    <Figure title="Headcount by department" loading={!departments}>
      <Group align="center" wrap="nowrap" gap="lg">
        <DonutChart data={slices} size={180} thickness={28} strokeWidth={2} tooltipDataSource="segment" />
        {/* The legend carries the numbers, so identity never rests on color alone. */}
        <Stack component="ul" gap={6} p={0} m={0} style={{ listStyle: 'none' }}>
          {slices.map((s) => (
            <Group component="li" key={s.name} aria-label={s.name} gap={8} wrap="nowrap">
              <Box w={10} h={10} style={{ borderRadius: 2, background: s.color, flexShrink: 0 }} />
              <Text size="sm">{s.name}</Text>
              <Text size="sm" c="dimmed" ff="monospace">
                {formatNumber(s.value)} · {Math.round((s.value / total) * 100)}%
              </Text>
            </Group>
          ))}
        </Stack>
      </Group>
    </Figure>
  )
}

export function LevelGapChart({ levels }: { levels?: LevelStats[] }) {
  const gaps = (levels ?? []).filter((l) => l.gap_to_previous_pct !== null)
  return (
    <Figure
      title="Pay vs the level below"
      caption="Median pay compared with the level below for the same job title and country. Org-wide medians mix countries, so they can mislead."
      loading={!levels}
    >
      <BarChart
        h={220}
        data={gaps}
        dataKey="job_level"
        series={[{ name: 'gap_to_previous_pct', label: 'vs level below', color: BRAND }]}
        valueFormatter={pct}
        gridAxis="y"
        barProps={{ radius: [4, 4, 0, 0] }}
        maxBarWidth={48}
      />
    </Figure>
  )
}

export function AverageVsMedianChart({ departments }: { departments?: DepartmentStats[] }) {
  const ranked = [...(departments ?? [])].sort((a, b) => b.average_salary_usd - a.average_salary_usd)
  return (
    <Figure
      title="Average vs median salary by department (USD)"
      caption="An average well above the median means a few high earners pull it up."
      loading={!departments}
    >
      <BarChart
        h={Math.max(200, ranked.length * 44)}
        data={ranked}
        dataKey="department"
        orientation="vertical"
        yAxisProps={{ width: 96, interval: 0 }}
        series={[
          { name: 'average_salary_usd', label: 'Average', color: CATEGORICAL[0] },
          { name: 'median_salary_usd', label: 'Median', color: CATEGORICAL[1] },
        ]}
        withLegend
        legendProps={{ verticalAlign: 'top' }}
        valueFormatter={usd}
        gridAxis="x"
        barProps={{ radius: [0, 4, 4, 0] }}
        barChartProps={{ barGap: 2 }}
        maxBarWidth={14}
      />
    </Figure>
  )
}

/** Changes and raises have different scales, so they get a chart each (never two y-axes). */
export function TrendCharts({ trend }: { trend?: SalaryTrend }) {
  const months = (trend?.months ?? []).map((m) => ({ ...m, label: monthLabel.format(new Date(`${m.month}-01T00:00:00Z`)) }))
  return (
    <>
      <Figure
        title="Salary changes per month"
        caption={trend && `${formatNumber(trend.changes)} changes for ${formatNumber(trend.employees)} employees in the last 12 months, by effective date.`}
        loading={!trend}
      >
        <BarChart
          h={220}
          data={months}
          dataKey="label"
          series={[{ name: 'changes', label: 'Salary changes', color: BRAND }]}
          valueFormatter={formatNumber}
          gridAxis="y"
          barProps={{ radius: [4, 4, 0, 0] }}
          maxBarWidth={28}
          xAxisProps={{ interval: 0 }}
        />
      </Figure>
      <Figure
        title="Average raise per month (%)"
        caption={
          trend?.average_raise_pct != null
            ? `${trend.average_raise_pct.toFixed(1)}% on average; currency moves are not counted as raises.`
            : undefined
        }
        loading={!trend}
      >
        <LineChart
          h={220}
          data={months}
          dataKey="label"
          series={[{ name: 'average_raise_pct', label: 'Average raise', color: BRAND }]}
          valueFormatter={(v) => `${v.toFixed(1)}%`}
          gridAxis="y"
          curveType="linear"
          strokeWidth={2}
          dotProps={{ r: 4 }}
          connectNulls={false}
          xAxisProps={{ interval: 0 }}
        />
      </Figure>
    </>
  )
}
