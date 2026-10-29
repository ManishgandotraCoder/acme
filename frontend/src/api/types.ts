// Mirrors backend/app/schemas.py

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

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
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

export interface OrgSummary {
  headcount: number
  country_count: number
  total_payroll_usd: number
  average_salary_usd: number
  fx_rates_as_of: string
}

export interface CountryStats {
  country: string
  currency: string
  headcount: number
  min_salary: number
  max_salary: number
  average_salary: number
  median_salary: number
  average_salary_usd: number
}

export interface JobTitleStats {
  job_title: string
  currency: string
  headcount: number
  min_salary: number
  max_salary: number
  average_salary: number
}

export interface DepartmentStats {
  department: string
  headcount: number
  total_payroll_usd: number
  average_salary_usd: number
}

export interface AskResult {
  question: string
  answer: string
  intent: {
    metric: string
    country: string | null
    job_title: string | null
    department: string | null
  }
  data: Record<string, unknown>[]
}
