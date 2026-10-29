import { BarChart } from '@mantine/charts'
import { Alert, Group, Paper, Select, SimpleGrid, Skeleton, Stack, Table, Text, Title } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api'
import { formatMoney, formatNumber } from '../../lib/format'

export function InsightsPage() {
  const summary = useQuery({ queryKey: ['insights', 'summary'], queryFn: api.summary })
  const countries = useQuery({ queryKey: ['insights', 'countries'], queryFn: api.countryStats })

  const error = summary.error ?? countries.error
  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>Pay insights</Title>
        <Text c="dimmed" size="sm">
          Salaries are stored in local currency. Cross-country figures are converted to USD at static
          FX rates as of {summary.data?.fx_rates_as_of ?? '…'}.
        </Text>
      </div>
      {error && <Alert color="red">{error.message}</Alert>}

      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <Stat label="Headcount" value={summary.data && formatNumber(summary.data.headcount)} />
        <Stat label="Countries" value={summary.data && formatNumber(summary.data.country_count)} />
        <Stat label="Annual payroll" value={summary.data && formatMoney(summary.data.total_payroll_usd, 'USD')} />
        <Stat label="Average salary" value={summary.data && formatMoney(summary.data.average_salary_usd, 'USD')} />
      </SimpleGrid>

      <Section title="Pay by country">
        {countries.data && (
          <BarChart
            h={Math.max(160, countries.data.length * 34)}
            data={[...countries.data].sort((a, b) => b.average_salary_usd - a.average_salary_usd)}
            dataKey="country"
            orientation="vertical"
            yAxisProps={{ width: 110 }}
            series={[{ name: 'average_salary_usd', label: 'Average salary (USD)', color: 'indigo.6' }]}
            valueFormatter={(v) => formatMoney(v, 'USD')}
            gridAxis="x"
            barProps={{ radius: [0, 4, 4, 0] }}
            mb="md"
          />
        )}
        <Table.ScrollContainer minWidth={720}>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Country</Table.Th>
                <Table.Th ta="right">Headcount</Table.Th>
                <Table.Th ta="right">Min</Table.Th>
                <Table.Th ta="right">Median</Table.Th>
                <Table.Th ta="right">Average</Table.Th>
                <Table.Th ta="right">Max</Table.Th>
                <Table.Th ta="right">Average (USD)</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {countries.data?.map((c) => (
                <Table.Tr key={c.country}>
                  <Table.Td>{c.country}</Table.Td>
                  <Num>{formatNumber(c.headcount)}</Num>
                  <Num>{formatMoney(c.min_salary, c.currency)}</Num>
                  <Num>{formatMoney(c.median_salary, c.currency)}</Num>
                  <Num>{formatMoney(c.average_salary, c.currency)}</Num>
                  <Num>{formatMoney(c.max_salary, c.currency)}</Num>
                  <Num>{formatMoney(c.average_salary_usd, 'USD')}</Num>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Section>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <JobTitlesSection countries={countries.data?.map((c) => c.country) ?? []} />
        <DepartmentsSection countries={countries.data?.map((c) => c.country) ?? []} />
      </SimpleGrid>
    </Stack>
  )
}

function JobTitlesSection({ countries }: { countries: string[] }) {
  const [selected, setSelected] = useState<string | null>(null)
  const country = selected ?? countries[0] ?? null
  const stats = useQuery({
    queryKey: ['insights', 'job-titles', country],
    queryFn: () => api.jobTitleStats(country!),
    enabled: country !== null,
  })

  return (
    <Section
      title="Pay by job title"
      control={
        <Select aria-label="Country for job titles" data={countries} value={country} onChange={setSelected} allowDeselect={false} w={180} />
      }
    >
      {stats.error && <Alert color="red">{stats.error.message}</Alert>}
      <Table.ScrollContainer minWidth={480}>
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Job title</Table.Th>
              <Table.Th ta="right">People</Table.Th>
              <Table.Th ta="right">Min</Table.Th>
              <Table.Th ta="right">Average</Table.Th>
              <Table.Th ta="right">Max</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {stats.data?.map((s) => (
              <Table.Tr key={s.job_title}>
                <Table.Td>{s.job_title}</Table.Td>
                <Num>{formatNumber(s.headcount)}</Num>
                <Num>{formatMoney(s.min_salary, s.currency)}</Num>
                <Num>{formatMoney(s.average_salary, s.currency)}</Num>
                <Num>{formatMoney(s.max_salary, s.currency)}</Num>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Section>
  )
}

function DepartmentsSection({ countries }: { countries: string[] }) {
  const [country, setCountry] = useState<string | null>(null)
  const stats = useQuery({
    queryKey: ['insights', 'departments', country],
    queryFn: () => api.departmentStats(country ?? undefined),
  })

  return (
    <Section
      title="Pay by department"
      control={
        <Select
          aria-label="Country for departments"
          placeholder="All countries"
          clearable
          data={countries}
          value={country}
          onChange={setCountry}
          w={180}
        />
      }
    >
      {stats.error && <Alert color="red">{stats.error.message}</Alert>}
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Department</Table.Th>
            <Table.Th ta="right">People</Table.Th>
            <Table.Th ta="right">Average (USD)</Table.Th>
            <Table.Th ta="right">Total payroll (USD)</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {stats.data?.map((d) => (
            <Table.Tr key={d.department}>
              <Table.Td>{d.department}</Table.Td>
              <Num>{formatNumber(d.headcount)}</Num>
              <Num>{formatMoney(d.average_salary_usd, 'USD')}</Num>
              <Num>{formatMoney(d.total_payroll_usd, 'USD')}</Num>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Section>
  )
}

function Stat({ label, value }: { label: string; value?: string }) {
  return (
    <Paper withBorder p="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
        {label}
      </Text>
      {value ? (
        <Text size="xl" fw={700}>
          {value}
        </Text>
      ) : (
        <Skeleton h={28} mt={4} />
      )}
    </Paper>
  )
}

function Section({ title, control, children }: { title: string; control?: React.ReactNode; children: React.ReactNode }) {
  return (
    <Paper withBorder p="md">
      <Group justify="space-between" mb="sm">
        <Title order={4}>{title}</Title>
        {control}
      </Group>
      {children}
    </Paper>
  )
}

function Num({ children }: { children: React.ReactNode }) {
  return (
    <Table.Td ta="right" ff="monospace">
      {children}
    </Table.Td>
  )
}
