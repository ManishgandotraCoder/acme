import { request } from './client'
import type {
  AskResult,
  CountryStats,
  DepartmentStats,
  Employee,
  EmployeeInput,
  EmployeeQuery,
  EmployeeUpdate,
  JobTitleStats,
  Meta,
  OrgSummary,
  Page,
  SalaryChange,
} from './types'

export const api = {
  meta: () => request<Meta>('/api/meta'),

  listEmployees: (query: EmployeeQuery) =>
    request<Page<Employee>>('/api/employees', { query: { ...query } }),
  createEmployee: (body: EmployeeInput) =>
    request<Employee>('/api/employees', { method: 'POST', body }),
  updateEmployee: (id: number, body: EmployeeUpdate) =>
    request<Employee>(`/api/employees/${id}`, { method: 'PATCH', body }),
  deleteEmployee: (id: number) => request<void>(`/api/employees/${id}`, { method: 'DELETE' }),
  salaryHistory: (id: number) => request<SalaryChange[]>(`/api/employees/${id}/salary-history`),

  summary: () => request<OrgSummary>('/api/insights/summary'),
  countryStats: () => request<CountryStats[]>('/api/insights/countries'),
  jobTitleStats: (country: string) =>
    request<JobTitleStats[]>('/api/insights/job-titles', { query: { country } }),
  departmentStats: (country?: string) =>
    request<DepartmentStats[]>('/api/insights/departments', { query: { country } }),

  ask: (question: string) =>
    request<AskResult>('/api/ask', { method: 'POST', body: { question } }),
}

export { ApiError } from './client'
export type * from './types'
