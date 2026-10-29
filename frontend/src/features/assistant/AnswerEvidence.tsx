import { BarChart } from '@mantine/charts'
import { Box, Table } from '@mantine/core'
import type { AskResult, Column } from '@/features/assistant/types'
import { formatValue } from './valueFormat'

/** The rows behind an answer: a bar chart for comparisons and a compact table. */
export function AnswerEvidence({ result }: { result: AskResult }) {
  const { table, chart } = result
  if (!table) return null

  // Hidden (privacy) values can't be plotted; leave them out of the chart only.
  const plotted = chart ? table.rows.filter((row) => typeof row[chart.y] === 'number') : []
  const yFormat = table.columns.find((c) => c.key === chart?.y)?.format ?? 'number'

  return (
    <>
      {chart && plotted.length > 1 && (
        <Box aria-label={`Chart: ${chart.label}`} role="img" mt="xs">
          <BarChart
            h={Math.min(220, Math.max(120, plotted.length * 26))}
            data={plotted}
            dataKey={chart.x}
            orientation="vertical"
            yAxisProps={{ width: 96, interval: 0 }}
            series={[{ name: chart.y, label: chart.label, color: 'brand.6' }]}
            valueFormatter={(v) => formatValue(v, yFormat)}
            gridAxis="x"
            barProps={{ radius: [0, 4, 4, 0] }}
            maxBarWidth={14}
          />
        </Box>
      )}
      <Table.ScrollContainer minWidth={0} mt="xs" type="native">
        <Table fz="xs" verticalSpacing={4} horizontalSpacing={6} striped withTableBorder>
          <Table.Thead>
            <Table.Tr>
              {table.columns.map((column) => (
                <Table.Th key={column.key} ta={column.format === 'text' ? 'left' : 'right'} style={{ whiteSpace: 'nowrap' }}>
                  {column.label}
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {table.rows.map((row, index) => (
              <Table.Tr key={index}>
                {table.columns.map((column) => (
                  <Table.Td
                    key={column.key}
                    ta={column.format === 'text' ? 'left' : 'right'}
                    ff={column.format === 'text' ? undefined : 'monospace'}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    {formatCell(row, column)}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </>
  )
}

/** "—" marks a value hidden to protect a small group's privacy. */
function formatCell(row: Record<string, unknown>, column: Column): string {
  const value = row[column.key]
  if (value === null || value === undefined) return '—'
  if (typeof value !== 'number') return String(value)
  return formatValue(value, column.format, String(row.currency))
}
