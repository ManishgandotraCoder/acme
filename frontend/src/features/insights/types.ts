// Mirrors backend/app/modules/insights/schemas.py

export interface OrgSummary {
  headcount: number
  country_count: number
  total_payroll_usd: number
  average_salary_usd: number
  median_salary_usd: number
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
  median_salary_usd: number
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
  median_salary_usd: number
}

export interface LevelStats {
  job_level: string
  headcount: number
  average_salary_usd: number
  median_salary_usd: number
  /** Median pay vs the level below for the same job title and country (%); null for the first. */
  gap_to_previous_pct: number | null
}

export interface SalaryBand {
  label: string
  min_usd: number
  max_usd: number | null
  headcount: number
}

export interface MonthlyTrend {
  month: string // YYYY-MM
  changes: number
  average_raise_pct: number | null
}

export interface SalaryTrend {
  start: string
  end: string
  changes: number
  employees: number
  average_raise_pct: number | null
  months: MonthlyTrend[]
}
