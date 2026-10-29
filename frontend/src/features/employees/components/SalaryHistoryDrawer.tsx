import { Alert, Drawer, Skeleton, Stack, Text, Timeline } from '@mantine/core'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { LoadingStatus } from '@/shared/ui/loading'
import { useSalaryHistory } from '../hooks'
import type { Employee } from '@/features/employees/types'

export function SalaryHistoryDrawer({ employee, onClose }: { employee: Employee | null; onClose: () => void }) {
  const history = useSalaryHistory(employee?.id ?? null)

  return (
    <Drawer opened={employee !== null} onClose={onClose} position="right" title={`Salary history · ${employee?.full_name ?? ''}`}>
      {history.isLoading && (
        <Stack gap="lg" mt="xs">
          <LoadingStatus label="Loading salary history…" />
          {[0, 1, 2].map((i) => (
            <div key={i}>
              <Skeleton h={14} w="70%" />
              <Skeleton h={10} w="35%" mt={8} />
            </div>
          ))}
        </Stack>
      )}
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
