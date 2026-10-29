import {
  ActionIcon,
  Alert,
  Button,
  Group,
  Modal,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { IconHistory, IconPencil, IconPlus, IconSearch, IconTrash } from '@tabler/icons-react'
import { useState } from 'react'
import type { Employee, EmployeeInput, EmployeeQuery, EmployeeUpdate } from '../../api'
import { formatDate, formatMoney, formatNumber } from '../../lib/format'
import { EmployeeForm } from './EmployeeForm'
import { SalaryHistoryDrawer } from './SalaryHistoryDrawer'
import {
  useCreateEmployee,
  useDeleteEmployee,
  useEmployees,
  useMeta,
  useUpdateEmployee,
} from './useEmployees'

const PAGE_SIZE = 25

const SORT_OPTIONS = [
  { value: 'full_name:asc', label: 'Name (A–Z)' },
  { value: 'annual_salary:desc', label: 'Salary, in USD terms (high → low)' },
  { value: 'annual_salary:asc', label: 'Salary, in USD terms (low → high)' },
  { value: 'hire_date:desc', label: 'Newest hires' },
  { value: 'hire_date:asc', label: 'Longest tenure' },
]

type Filters = Pick<EmployeeQuery, 'country' | 'department' | 'job_title'>

export function EmployeesPage() {
  const [search, setSearch] = useState('')
  const [debouncedSearch] = useDebouncedValue(search, 300)
  const [filters, setFilters] = useState<Filters>({})
  const [sort, setSort] = useState(SORT_OPTIONS[0].value)
  const [page, setPage] = useState(1)

  const [editing, setEditing] = useState<Employee | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Employee | null>(null)
  const [historyFor, setHistoryFor] = useState<Employee | null>(null)

  const [sortField, order] = sort.split(':') as [EmployeeQuery['sort'], EmployeeQuery['order']]
  const meta = useMeta()
  const employees = useEmployees({
    search: debouncedSearch,
    ...filters,
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

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>Employees</Title>
          <Text c="dimmed" size="sm">
            {formatNumber(total)} employees
          </Text>
        </div>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setEditing('new')} disabled={!meta.data}>
          Add employee
        </Button>
      </Group>

      <Group grow align="flex-end" wrap="wrap">
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
      </Group>

      {employees.error && <Alert color="red">{employees.error.message}</Alert>}

      <Paper withBorder>
        <Table.ScrollContainer minWidth={800}>
          <Table striped highlightOnHover verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th>Job title</Table.Th>
                <Table.Th>Department</Table.Th>
                <Table.Th>Country</Table.Th>
                <Table.Th ta="right">Annual salary</Table.Th>
                <Table.Th>Hired</Table.Th>
                <Table.Th w={110} />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {employees.data?.items.map((e) => (
                <Table.Tr key={e.id}>
                  <Table.Td>
                    <Text size="sm" fw={500}>
                      {e.full_name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {e.email}
                    </Text>
                  </Table.Td>
                  <Table.Td>{e.job_title}</Table.Td>
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
                  <Table.Td colSpan={7}>
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
