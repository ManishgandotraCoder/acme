import {
  ActionIcon,
  Badge,
  Button,
  Collapse,
  Group,
  Input,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import { IconAdjustmentsHorizontal, IconArrowsSort, IconSearch, IconX } from '@tabler/icons-react'
import { useState } from 'react'
import { formatNumber } from '@/shared/lib/format'
import type { Meta } from '@/features/employees/types'
import { SORT_OPTIONS, type Amount, type Filters } from './directoryOptions'

const FILTER_LABELS: Record<keyof Filters, string> = {
  country: 'Country',
  department: 'Department',
  job_title: 'Job title',
  job_level: 'Level',
  currency: 'Currency',
}

interface Props {
  meta?: Meta
  search: string
  onSearch: (value: string) => void
  filters: Filters
  onFilter: (key: keyof Filters, value: string | null) => void
  salaryMin: Amount
  salaryMax: Amount
  onSalaryMin: (value: Amount) => void
  onSalaryMax: (value: Amount) => void
  /** The currency salary bounds are compared in (see EmployeeFilter on the backend). */
  rangeCurrency: string
  sort: string
  onSort: (value: string) => void
  onClearAll: () => void
}

/** Search and sort on top; labelled filters in a panel that folds away on small screens. */
export function DirectoryToolbar(props: Props) {
  const { meta, filters, onFilter, rangeCurrency } = props
  const small = useMediaQuery('(max-width: 48em)')
  const [opened, setOpened] = useState<boolean | null>(null)
  const panelOpen = opened ?? !small

  const chips = [
    ...(Object.keys(FILTER_LABELS) as (keyof Filters)[])
      .filter((key) => filters[key])
      .map((key) => ({ label: `${FILTER_LABELS[key]}: ${filters[key]}`, clear: () => onFilter(key, null) })),
    ...(typeof props.salaryMin === 'number'
      ? [{ label: `Salary ≥ ${rangeCurrency} ${formatNumber(props.salaryMin)}`, clear: () => props.onSalaryMin('') }]
      : []),
    ...(typeof props.salaryMax === 'number'
      ? [{ label: `Salary ≤ ${rangeCurrency} ${formatNumber(props.salaryMax)}`, clear: () => props.onSalaryMax('') }]
      : []),
  ]
  const currencies = [...new Set(meta?.countries.map((c) => c.currency) ?? [])].sort()

  return (
    <Paper withBorder p="sm">
      <Stack gap="sm">
        <Group gap="sm" wrap="wrap">
          <TextInput
            flex="1 1 240px"
            placeholder="Search name or email"
            leftSection={<IconSearch size={16} />}
            value={props.search}
            onChange={(e) => props.onSearch(e.currentTarget.value)}
            aria-label="Search employees"
          />
          <Select
            flex="0 1 290px"
            miw={200}
            aria-label="Sort by"
            leftSection={<IconArrowsSort size={16} />}
            data={SORT_OPTIONS}
            value={props.sort}
            allowDeselect={false}
            onChange={(v) => v && props.onSort(v)}
          />
          <Button
            variant={panelOpen ? 'light' : 'default'}
            leftSection={<IconAdjustmentsHorizontal size={16} />}
            rightSection={chips.length > 0 && <Badge size="sm" circle>{chips.length}</Badge>}
            aria-label={chips.length ? `Filters, ${chips.length} active` : 'Filters'}
            aria-expanded={panelOpen}
            onClick={() => setOpened(!panelOpen)}
          >
            Filters
          </Button>
        </Group>

        <Collapse in={panelOpen}>
          <SimpleGrid cols={{ base: 1, xs: 2, md: 3, lg: 6 }} spacing="sm" verticalSpacing="xs">
            <Select
              label="Country"
              aria-label="Filter by country"
              placeholder="All countries"
              clearable
              searchable
              data={meta?.countries.map((c) => c.name) ?? []}
              value={filters.country ?? null}
              onChange={(v) => onFilter('country', v)}
            />
            <Select
              label="Department"
              aria-label="Filter by department"
              placeholder="All departments"
              clearable
              data={meta?.departments ?? []}
              value={filters.department ?? null}
              onChange={(v) => onFilter('department', v)}
            />
            <Select
              label="Job title"
              aria-label="Filter by job title"
              placeholder="All job titles"
              clearable
              searchable
              data={meta?.job_titles ?? []}
              value={filters.job_title ?? null}
              onChange={(v) => onFilter('job_title', v)}
            />
            <Select
              label="Level"
              aria-label="Filter by job level"
              placeholder="All levels"
              clearable
              data={meta?.job_levels ?? []}
              value={filters.job_level ?? null}
              onChange={(v) => onFilter('job_level', v)}
            />
            <Select
              label="Currency"
              aria-label="Filter by currency"
              placeholder="All currencies"
              clearable
              data={currencies}
              value={filters.currency ?? null}
              onChange={(v) => onFilter('currency', v)}
            />
            {/* Same wrapper as the selects, so the label lines up with theirs. */}
            <Input.Wrapper label={`Salary (${rangeCurrency})`}>
              <Group gap={6} wrap="nowrap">
                <NumberInput
                  flex={1}
                  placeholder="Min"
                  aria-label={`Minimum salary (${rangeCurrency})`}
                  min={0}
                  allowDecimal={false}
                  thousandSeparator=","
                  hideControls
                  value={props.salaryMin}
                  onChange={props.onSalaryMin}
                />
                <Text c="dimmed">–</Text>
                <NumberInput
                  flex={1}
                  placeholder="Max"
                  aria-label={`Maximum salary (${rangeCurrency})`}
                  min={0}
                  allowDecimal={false}
                  thousandSeparator=","
                  hideControls
                  value={props.salaryMax}
                  onChange={props.onSalaryMax}
                />
              </Group>
            </Input.Wrapper>
          </SimpleGrid>
        </Collapse>

        {chips.length > 0 && (
          <Group gap={6} justify="space-between" wrap="nowrap" align="flex-start">
            <Group component="ul" aria-label="Active filters" gap={6} p={0} m={0} style={{ listStyle: 'none' }}>
              {chips.map((chip) => (
                <Badge
                  component="li"
                  key={chip.label}
                  variant="light"
                  size="lg"
                  tt="none"
                  fw={500}
                  pr={4}
                  rightSection={
                    <ActionIcon
                      size="xs"
                      variant="transparent"
                      aria-label={`Remove filter ${chip.label}`}
                      onClick={chip.clear}
                    >
                      <IconX size={12} />
                    </ActionIcon>
                  }
                >
                  {chip.label}
                </Badge>
              ))}
            </Group>
            <Button variant="subtle" size="compact-sm" onClick={props.onClearAll} style={{ flexShrink: 0 }}>
              Clear all
            </Button>
          </Group>
        )}
      </Stack>
    </Paper>
  )
}
