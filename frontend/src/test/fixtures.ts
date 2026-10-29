import type { Employee, Meta } from '@/features/employees/types'

export const meta: Meta = {
  countries: [
    { name: 'India', currency: 'INR' },
    { name: 'United Kingdom', currency: 'GBP' },
  ],
  departments: ['Engineering', 'Sales'],
  job_titles: ['Account Executive', 'Software Engineer'],
}

export function buildEmployee(overrides: Partial<Employee> = {}): Employee {
  return {
    id: 1,
    full_name: 'Ada Lovelace',
    email: 'ada@example.com',
    job_title: 'Software Engineer',
    department: 'Engineering',
    country: 'United Kingdom',
    currency: 'GBP',
    annual_salary: 80000,
    hire_date: '2020-01-15',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}
