import { Alert, Drawer, Loader, Text, Timeline } from '@mantine/core'
import type { Employee } from '../../api'
import { formatDate, formatMoney } from '../../lib/format'
import { useSalaryHistory } from './useEmployees'

export function SalaryHistoryDrawer({ employee, onClose }: { employee: Employee | null; onClose: () => void }) {
  const history = useSalaryHistory(employee?.id ?? null)

  return (
    <Drawer opened={employee !== null} onClose={onClose} position="right" title={`Salary history · ${employee?.full_name ?? ''}`}>
      {history.isLoading && <Loader size="sm" />}
      {history.error && <Alert color="red">{history.error.message}</Alert>}
      {history.data?.length === 0 && (
        <Text c="dimmed">No salary changes recorded since this employee was added.</Text>
      )}
      {history.data && history.data.length > 0 && (
        <Timeline bulletSize={14} lineWidth={2}>
          {history.data.map((change) => (
            <Timeline.Item
              key={change.id}
              title={`${formatMoney(change.previous_salary, change.previous_currency)} → ${formatMoney(change.new_salary, change.new_currency)}`}
            >
              {change.reason && <Text size="sm">{change.reason}</Text>}
              <Text size="xs" c="dimmed">
                {formatDate(change.changed_at)}
              </Text>
            </Timeline.Item>
          ))}
        </Timeline>
      )}
    </Drawer>
  )
}
