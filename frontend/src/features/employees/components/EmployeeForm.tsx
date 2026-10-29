import { Alert, Autocomplete, Button, Group, NumberInput, Select, SimpleGrid, Stack, TextInput } from '@mantine/core'
import { useForm } from '@mantine/form'
import type { Employee, EmployeeInput, EmployeeUpdate, Meta } from '@/features/employees/types'

interface FormValues {
  full_name: string
  email: string
  job_title: string
  department: string
  country: string | null
  annual_salary: number | string
  hire_date: string
  salary_change_reason: string
}

interface Props {
  meta: Meta
  /** When provided the form edits this employee and submits only changed fields. */
  employee?: Employee
  onSubmit: (values: EmployeeInput | EmployeeUpdate) => void
  submitting?: boolean
  error?: string | null
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const today = () => new Date().toISOString().slice(0, 10)

export function EmployeeForm({ meta, employee, onSubmit, submitting, error }: Props) {
  const form = useForm<FormValues>({
    initialValues: {
      full_name: employee?.full_name ?? '',
      email: employee?.email ?? '',
      job_title: employee?.job_title ?? '',
      department: employee?.department ?? '',
      country: employee?.country ?? null,
      annual_salary: employee?.annual_salary ?? '',
      hire_date: employee?.hire_date ?? '',
      salary_change_reason: '',
    },
    validate: {
      full_name: (v) => (v.trim() ? null : 'Full name is required'),
      email: (v) => (EMAIL.test(v.trim()) ? null : 'Enter a valid email'),
      job_title: (v) => (v.trim() ? null : 'Job title is required'),
      department: (v) => (v.trim() ? null : 'Department is required'),
      country: (v) => (v ? null : 'Country is required'),
      annual_salary: (v) => (typeof v === 'number' && v > 0 ? null : 'Salary must be greater than 0'),
      hire_date: (v) => {
        if (!v) return 'Hire date is required'
        return v > today() ? 'Hire date cannot be in the future' : null
      },
    },
  })

  const currency = meta.countries.find((c) => c.name === form.values.country)?.currency
  const salaryChanged = employee !== undefined && form.values.annual_salary !== employee.annual_salary

  const handleSubmit = (values: FormValues) => {
    const payload: EmployeeInput = {
      full_name: values.full_name.trim(),
      email: values.email.trim(),
      job_title: values.job_title.trim(),
      department: values.department.trim(),
      country: values.country!,
      annual_salary: Number(values.annual_salary),
      hire_date: values.hire_date,
    }
    if (!employee) return onSubmit(payload)

    const changes: EmployeeUpdate = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => employee[key as keyof EmployeeInput] !== value),
    )
    if (salaryChanged && values.salary_change_reason.trim()) {
      changes.salary_change_reason = values.salary_change_reason.trim()
    }
    onSubmit(changes)
  }

  return (
    <form onSubmit={form.onSubmit(handleSubmit)} noValidate>
      <Stack>
        {error && (
          <Alert color="red" variant="light">
            {error}
          </Alert>
        )}
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput label="Full name" withAsterisk {...form.getInputProps('full_name')} />
          <TextInput label="Email" type="email" withAsterisk {...form.getInputProps('email')} />
          <Autocomplete label="Job title" withAsterisk data={meta.job_titles} {...form.getInputProps('job_title')} />
          <Autocomplete label="Department" withAsterisk data={meta.departments} {...form.getInputProps('department')} />
          <Select
            label="Country"
            withAsterisk
            searchable
            data={meta.countries.map((c) => c.name)}
            {...form.getInputProps('country')}
          />
          <TextInput label="Hire date" type="date" max={today()} withAsterisk {...form.getInputProps('hire_date')} />
          <NumberInput
            label={currency ? `Annual salary (${currency})` : 'Annual salary'}
            withAsterisk
            min={1}
            allowDecimal={false}
            thousandSeparator=","
            {...form.getInputProps('annual_salary')}
          />
          {salaryChanged && (
            <TextInput
              label="Reason for salary change"
              placeholder="e.g. Promotion, annual review"
              {...form.getInputProps('salary_change_reason')}
            />
          )}
        </SimpleGrid>
        <Group justify="flex-end">
          <Button type="submit" loading={submitting}>
            Save
          </Button>
        </Group>
      </Stack>
    </form>
  )
}
