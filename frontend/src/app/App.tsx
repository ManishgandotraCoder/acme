import { Anchor, AppShell, Container, Group, ThemeIcon, Title } from '@mantine/core'
import { IconCoin } from '@tabler/icons-react'
import { lazy, Suspense } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { ChatWidget, type OpenAssistantState } from '@/features/assistant/ChatWidget'
import { PageSkeleton } from '@/shared/ui/loading'

// Route-level code splitting: the charting library is only downloaded for Pay insights.
const EmployeesPage = lazy(() => import('@/features/employees/EmployeesPage').then((m) => ({ default: m.EmployeesPage })))
const InsightsPage = lazy(() => import('@/features/insights/InsightsPage').then((m) => ({ default: m.InsightsPage })))

const openAssistant: OpenAssistantState = { openAssistant: true }

export function App() {
  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Container size="xl" h="100%">
          <Group h="100%">
            <Anchor component={Link} to="/" underline="never" c="inherit">
              <Group gap="xs">
                <ThemeIcon radius="md" size="lg">
                  <IconCoin size={20} />
                </ThemeIcon>
                <Title order={4}>ACME Salary Management</Title>
              </Group>
            </Anchor>
          </Group>
        </Container>
      </AppShell.Header>

      {/* Bottom padding keeps the chat launcher from covering pagination. */}
      <AppShell.Main pb={96}>
        <Container size="xl" p={0}>
          <Suspense fallback={<PageSkeleton />}>
            <Routes>
              <Route path="/" element={<EmployeesPage />} />
              <Route path="/insights" element={<InsightsPage />} />
              <Route path="/employees" element={<Navigate to="/" replace />} />
              <Route path="/ask" element={<Navigate to="/" replace state={openAssistant} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </Container>
      </AppShell.Main>

      <ChatWidget />
    </AppShell>
  )
}
