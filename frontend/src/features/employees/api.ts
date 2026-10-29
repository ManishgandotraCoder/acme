import { request } from '@/shared/api/client'
import type { Page } from '@/shared/api/types'
import type { Employee, EmployeeInput, EmployeeQuery, EmployeeUpdate, Meta, SalaryChange } from './types'

export const employeesApi = {
  meta: () => request<Meta>('/api/meta'),
  list: (query: EmployeeQuery) => request<Page<Employee>>('/api/employees', { query: { ...query } }),
  create: (body: EmployeeInput) => request<Employee>('/api/employees', { method: 'POST', body }),
  update: (id: number, body: EmployeeUpdate) =>
    request<Employee>(`/api/employees/${id}`, { method: 'PATCH', body }),
  remove: (id: number) => request<void>(`/api/employees/${id}`, { method: 'DELETE' }),
  salaryHistory: (id: number) => request<SalaryChange[]>(`/api/employees/${id}/salary-history`),
}
