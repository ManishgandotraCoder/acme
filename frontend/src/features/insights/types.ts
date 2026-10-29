// Mirrors backend/app/modules/insights/schemas.py

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
