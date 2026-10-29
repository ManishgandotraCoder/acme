import { request } from '@/shared/api/client'
import type {
  CountryStats,
  DepartmentStats,
  JobTitleStats,
  LevelStats,
  OrgSummary,
  SalaryBand,
  SalaryTrend,
} from './types'

export const insightsApi = {
  summary: () => request<OrgSummary>('/api/insights/summary'),
  countries: () => request<CountryStats[]>('/api/insights/countries'),
  jobTitles: (country: string) =>
    request<JobTitleStats[]>('/api/insights/job-titles', { query: { country } }),
  departments: (country?: string) =>
    request<DepartmentStats[]>('/api/insights/departments', { query: { country } }),
  levels: () => request<LevelStats[]>('/api/insights/levels'),
  salaryBands: () => request<SalaryBand[]>('/api/insights/salary-bands'),
  salaryTrends: () => request<SalaryTrend>('/api/insights/salary-trends'),
}
