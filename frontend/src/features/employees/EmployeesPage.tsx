import {
  ActionIcon,
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Pagination,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { IconChartBar, IconHistory, IconPencil, IconPlus, IconSearch, IconTrash } from '@tabler/icons-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { formatDate, formatMoney, formatNumber } from '@/shared/lib/format'
import { LoadingStatus, RefreshBar, SkeletonRows } from '@/shared/ui/loading'
import { EmployeeForm } from './components/EmployeeForm'
import { SalaryHistoryDrawer } from './components/SalaryHistoryDrawer'
import {
  useCreateEmployee,
  useDeleteEmployee,
  useEmployees,
  useMeta,
  useUpdateEmployee,
} from './hooks'
import type { Employee, EmployeeInput, EmployeeQuery, EmployeeUpdate } from '@/features/employees/types'

const PAGE_SIZE = 25

const SORT_OPTIONS = [
  { value: 'full_name:asc', label: 'Name (A–Z)' },
  { value: 'annual_salary:desc', label: 'Salary, in USD terms (high → low)' },
  { value: 'annual_salary:asc', label: 'Salary, in USD terms (low → high)' },
  { value: 'hire_date:desc', label: 'Newest hires' },
  { value: 'hire_date:asc', label: 'Longest tenure' },
]

type Filters = Pick<EmployeeQuery, 'country' | 'department' | 'job_title' | 'job_level' | 'currency'>
type Amount = number | string // NumberInput yields '' when cleared

const toBound = (value: Amount) => (typeof value === 'number' ? value : undefined)

export function EmployeesPage() {
  const [search, setSearch] = useState('')
  const [debouncedSearch] = useDebouncedValue(search, 300)
  const [filters, setFilters] = useState<Filters>({})
  const [salaryMin, setSalaryMin] = useState<Amount>('')
  const [salaryMax, setSalaryMax] = useState<Amount>('')
  const [[debouncedMin, debouncedMax]] = useDebouncedValue([salaryMin, salaryMax], 300)
  const [sort, setSort] = useState(SORT_OPTIONS[0].value)
  const [page, setPage] = useState(1)

  const [editing, setEditing] = useState<Employee | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Employee | null>(null)
  const [historyFor, setHistoryFor] = useState<Employee | null>(null)

  const [sortField, order] = sort.split(':') as [EmployeeQuery['sort'], EmployeeQuery['order']]
  const meta = useMeta()
  // Mirrors the backend rule: one currency pinned → compare local amounts, otherwise USD.
  const rangeCurrency =
    filters.currency ?? meta.data?.countries.find((c) => c.name === filters.country)?.currency ?? 'USD'
  const currencies = [...new Set(meta.data?.countries.map((c) => c.currency) ?? [])].sort()
  const employees = useEmployees({
    search: debouncedSearch,
    ...filters,
    salary_min: toBound(debouncedMin),
    salary_max: toBound(debouncedMax),
    page,
    page_size: PAGE_SIZE,
    sort: sortField,
    order,
  })

  const create = useCreateEmployee()
  const update = useUpdateEmployee()
  const remove = useDeleteEmployee()
  const saving = editing === 'new' ? create : update

  const setFilter = (key: keyof Filters) => (value: string | null) => {
    setFilters((f) => ({ ...f, [key]: value ?? undefined }))
    setPage(1)
  }
  const setBound = (set: (value: Amount) => void) => (value: Amount) => {
    set(value)
    setPage(1)
  }

  const closeForm = () => {
    setEditing(null)
    create.reset()
    update.reset()
  }

  const save = (body: EmployeeInput | EmployeeUpdate) => {
    const onSuccess = () => {
      notifications.show({ color: 'green', message: 'Employee saved' })
      closeForm()
    }
    if (editing === 'new') create.mutate(body as EmployeeInput, { onSuccess })
    else if (editing) update.mutate({ id: editing.id, body }, { onSuccess })
  }

  const confirmDelete = () => {
    if (!deleting) return
    remove.mutate(deleting.id, {
      onSuccess: () => {
        notifications.show({ message: `${deleting.full_name} removed` })
        setDeleting(null)
      },
    })
  }

  const total = employees.data?.total ?? 0
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  // Number rows from the page the server returned, so they stay right while the next page loads.
  const firstRowNumber = employees.data ? (employees.data.page - 1) * employees.data.page_size + 1 : 1

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>Employees</Title>
          <Text c="dimmed" size="sm">
            {employees.isPending ? 'Loading…' : `${formatNumber(total)} employees`}
          </Text>
        </div>
        <Group gap="sm">
          <Button component={Link} to="/insights" variant="light" leftSection={<IconChartBar size={16} />}>
            Pay insights
          </Button>
          <Button leftSection={<IconPlus size={16} />} onClick={() => setEditing('new')} disabled={!meta.data}>
            Add employee
          </Button>
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, xs: 2, md: 5 }} spacing="sm">
        <TextInput
          placeholder="Search name or email"
          leftSection={<IconSearch size={16} />}
          value={search}
          onChange={(e) => {
            setSearch(e.currentTarget.value)
            setPage(1)
          }}
          aria-label="Search employees"
        />
        <Select
          placeholder="All countries"
          aria-label="Filter by country"
          clearable
          searchable
          data={meta.data?.countries.map((c) => c.name) ?? []}
          value={filters.country ?? null}
          onChange={setFilter('country')}
        />
        <Select
          placeholder="All departments"
          aria-label="Filter by department"
          clearable
          data={meta.data?.departments ?? []}
          value={filters.department ?? null}
          onChange={setFilter('department')}
        />
        <Select
          placeholder="All job titles"
          aria-label="Filter by job title"
          clearable
          searchable
          data={meta.data?.job_titles ?? []}
          value={filters.job_title ?? null}
          onChange={setFilter('job_title')}
        />
        <Select
          aria-label="Sort by"
          data={SORT_OPTIONS}
          value={sort}
          allowDeselect={false}
          onChange={(v) => v && setSort(v)}
        />
        <Select
          placeholder="All levels"
          aria-label="Filter by job level"
          clearable
          data={meta.data?.job_levels ?? []}
          value={filters.job_level ?? null}
          onChange={setFilter('job_level')}
        />
        <Select
          placeholder="All currencies"
          aria-label="Filter by currency"
          clearable
          data={currencies}
          value={filters.currency ?? null}
          onChange={setFilter('currency')}
        />
        <NumberInput
          placeholder={`Min salary (${rangeCurrency})`}
          aria-label={`Minimum salary (${rangeCurrency})`}
          min={0}
          allowDecimal={false}
          thousandSeparator=","
          value={salaryMin}
          onChange={setBound(setSalaryMin)}
        />
        <NumberInput
          placeholder={`Max salary (${rangeCurrency})`}
          aria-label={`Maximum salary (${rangeCurrency})`}
          min={0}
          allowDecimal={false}
          thousandSeparator=","
          value={salaryMax}
          onChange={setBound(setSalaryMax)}
        />
      </SimpleGrid>

      {employees.error && <Alert color="red">{employees.error.message}</Alert>}

      <Paper withBorder style={{ overflow: 'hidden' }}>
        <RefreshBar active={employees.isFetching && !employees.isPending} />
        {employees.isPending && <LoadingStatus label="Loading employees…" />}
        <Table.ScrollContainer minWidth={800}>
          <Table striped highlightOnHover verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={64} ta="right">
                  #
                </Table.Th>
                <Table.Th>Name</Table.Th>
                <Table.Th>Job title</Table.Th>
                <Table.Th>Level</Table.Th>
                <Table.Th>Department</Table.Th>
                <Table.Th>Country</Table.Th>
                <Table.Th ta="right">Annual salary</Table.Th>
                <Table.Th>Hired</Table.Th>
                <Table.Th w={110} />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody style={{ opacity: employees.isPlaceholderData ? 0.6 : 1, transition: 'opacity 150ms' }}>
              {employees.isPending && <SkeletonRows rows={10} columns={9} />}
              {employees.data?.items.map((e, i) => (
                <Table.Tr key={e.id}>
                  <Table.Td ta="right" c="dimmed" ff="monospace" fz="sm">
                    {formatNumber(firstRowNumber + i)}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" fw={500}>
                      {e.full_name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {e.email}
                    </Text>
                  </Table.Td>
                  <Table.Td>{e.job_title}</Table.Td>
                  <Table.Td>{e.job_level}</Table.Td>
                  <Table.Td>{e.department}</Table.Td>
                  <Table.Td>{e.country}</Table.Td>
                  <Table.Td ta="right" ff="monospace">
                    {formatMoney(e.annual_salary, e.currency)}
                  </Table.Td>
                  <Table.Td>{formatDate(e.hire_date)}</Table.Td>
                  <Table.Td>
                    <Group gap={4} wrap="nowrap">
                      <RowAction label={`Edit ${e.full_name}`} onClick={() => setEditing(e)} icon={<IconPencil size={16} />} />
                      <RowAction label={`Salary history for ${e.full_name}`} onClick={() => setHistoryFor(e)} icon={<IconHistory size={16} />} />
                      <RowAction label={`Delete ${e.full_name}`} color="red" onClick={() => setDeleting(e)} icon={<IconTrash size={16} />} />
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {employees.data?.items.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={9}>
                    <Text c="dimmed" ta="center" py="lg">
                      No employees match these filters.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>

      <Group justify="flex-end">
        <Pagination total={pages} value={page} onChange={setPage} />
      </Group>

      <Modal
        opened={editing !== null}
        onClose={closeForm}
        title={editing === 'new' ? 'Add employee' : 'Edit employee'}
        size="lg"
      >
        {meta.data && editing !== null && (
          <EmployeeForm
            meta={meta.data}
            employee={editing === 'new' ? undefined : editing}
            onSubmit={save}
            submitting={saving.isPending}
            error={saving.error?.message}
          />
        )}
      </Modal>

      <Modal opened={deleting !== null} onClose={() => setDeleting(null)} title="Remove employee">
        <Stack>
          <Text>
            Remove <b>{deleting?.full_name}</b> and their salary history? This cannot be undone.
          </Text>
          {remove.error && <Alert color="red">{remove.error.message}</Alert>}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleting(null)}>
              Cancel
            </Button>
            <Button color="red" onClick={confirmDelete} loading={remove.isPending}>
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>

      <SalaryHistoryDrawer employee={historyFor} onClose={() => setHistoryFor(null)} />
    </Stack>
  )
}

function RowAction(props: { label: string; icon: React.ReactNode; onClick: () => void; color?: string }) {
  return (
    <Tooltip label={props.label} openDelay={400}>
      <ActionIcon variant="subtle" color={props.color ?? 'gray'} aria-label={props.label} onClick={props.onClick}>
        {props.icon}
      </ActionIcon>
    </Tooltip>
  )
}
