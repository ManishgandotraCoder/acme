import { Group, Loader, Paper, Progress, Skeleton, Stack, Table, Text, VisuallyHidden } from '@mantine/core'

// Varied widths read as "content is coming" rather than a grey block.
const WIDTHS = ['72%', '48%', '86%', '60%', '78%', '54%']

/** Announces loading to screen readers; sighted users see the skeleton. */
export function LoadingStatus({ label }: { label: string }) {
  return (
    <VisuallyHidden role="status" aria-live="polite">
      {label}
    </VisuallyHidden>
  )
}

/** Placeholder rows shaped like the real table. Render inside <Table.Tbody>. */
export function SkeletonRows({ rows = 8, columns }: { rows?: number; columns: number }) {
  return Array.from({ length: rows }, (_, r) => (
    <Table.Tr key={r} aria-hidden>
      {Array.from({ length: columns }, (_, c) => (
        <Table.Td key={c}>
          <Skeleton h={12} my={6} w={WIDTHS[(r + c) % WIDTHS.length]} />
        </Table.Td>
      ))}
    </Table.Tr>
  ))
}

/** Thin animated bar for background refreshes, so existing data stays readable. */
export function RefreshBar({ active }: { active: boolean }) {
  return (
    <Progress
      value={100}
      size={3}
      radius={0}
      animated
      aria-hidden
      style={{ visibility: active ? 'visible' : 'hidden' }}
    />
  )
}

/** Route-level fallback while a page's code downloads. */
export function PageSkeleton() {
  return (
    <Stack>
      <LoadingStatus label="Loading page…" />
      <div>
        <Skeleton h={28} w={220} />
        <Skeleton h={12} w={140} mt={10} />
      </div>
      <Group grow>
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} h={36} />
        ))}
      </Group>
      <Paper withBorder p="md">
        <Stack gap="sm">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} h={14} w={WIDTHS[i % WIDTHS.length]} />
          ))}
        </Stack>
      </Paper>
    </Stack>
  )
}

/** Inline "working on it" indicator with a label (e.g. while the LLM answers). */
export function WorkingIndicator({ label }: { label: string }) {
  return (
    <Group gap="xs">
      <Loader size="sm" />
      <Text size="sm" c="dimmed">
        {label}
      </Text>
    </Group>
  )
}
