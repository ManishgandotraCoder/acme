import type { EmployeeQuery } from '@/features/employees/types'

export type Filters = Pick<EmployeeQuery, 'country' | 'department' | 'job_title' | 'job_level' | 'currency'>
export type Amount = number | string // NumberInput yields '' when cleared

export const SORT_OPTIONS = [
  { value: 'full_name:asc', label: 'Name (A–Z)' },
  { value: 'full_name:desc', label: 'Name (Z–A)' },
  { value: 'annual_salary:desc', label: 'Salary, in USD terms (high → low)' },
  { value: 'annual_salary:asc', label: 'Salary, in USD terms (low → high)' },
  { value: 'hire_date:desc', label: 'Newest hires' },
  { value: 'hire_date:asc', label: 'Longest tenure' },
]
