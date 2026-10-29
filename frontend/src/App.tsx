import { AppShell, Burger, Group, Loader, NavLink, Title } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconChartBar, IconSparkles, IconUsers } from '@tabler/icons-react'
import { lazy, Suspense } from 'react'
import { NavLink as RouterLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'

// Route-level code splitting: the charting library is only downloaded for Pay insights.
const EmployeesPage = lazy(() => import('./features/employees/EmployeesPage').then((m) => ({ default: m.EmployeesPage })))
const InsightsPage = lazy(() => import('./features/insights/InsightsPage').then((m) => ({ default: m.InsightsPage })))
const AskPage = lazy(() => import('./features/ask/AskPage').then((m) => ({ default: m.AskPage })))

const NAV = [
  { to: '/employees', label: 'Employees', icon: IconUsers },
  { to: '/insights', label: 'Pay insights', icon: IconChartBar },
  { to: '/ask', label: 'Ask AI', icon: IconSparkles },
]

export function App() {
  const [opened, { toggle, close }] = useDisclosure()
  const { pathname } = useLocation()

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md">
          <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Toggle navigation" />
          <Title order={4}>ACME Salary Management</Title>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="xs">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            component={RouterLink}
            to={to}
            label={label}
            leftSection={<Icon size={18} />}
            active={pathname.startsWith(to)}
            onClick={close}
          />
        ))}
      </AppShell.Navbar>
      <AppShell.Main>
        <Suspense fallback={<Loader m="xl" />}>
          <Routes>
            <Route path="/" element={<Navigate to="/employees" replace />} />
            <Route path="/employees" element={<EmployeesPage />} />
            <Route path="/insights" element={<InsightsPage />} />
            <Route path="/ask" element={<AskPage />} />
          </Routes>
        </Suspense>
      </AppShell.Main>
    </AppShell>
  )
}
