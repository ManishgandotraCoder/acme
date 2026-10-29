// Mirrors backend/app/modules/employees/schemas.py

export interface Employee {
  id: number
  full_name: string
  email: string
  job_title: string
  department: string
  country: string
  currency: string
  annual_salary: number
  hire_date: string
  created_at: string
  updated_at: string
}

export type EmployeeInput = Pick<
  Employee,
  'full_name' | 'email' | 'job_title' | 'department' | 'country' | 'annual_salary' | 'hire_date'
>

export type EmployeeUpdate = Partial<EmployeeInput> & { salary_change_reason?: string }

export interface SalaryChange {
  id: number
  previous_salary: number
  new_salary: number
  previous_currency: string
  new_currency: string
  reason: string | null
  changed_at: string
}

export type SortField = 'full_name' | 'annual_salary' | 'hire_date'

export interface EmployeeQuery {
  search?: string
  country?: string
  department?: string
  job_title?: string
  page: number
  page_size: number
  sort: SortField
  order: 'asc' | 'desc'
}

export interface Meta {
  countries: { name: string; currency: string }[]
  departments: string[]
  job_titles: string[]
}
