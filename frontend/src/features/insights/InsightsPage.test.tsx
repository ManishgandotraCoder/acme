import { screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '@/test/render'
import { InsightsPage } from './InsightsPage'
import { insightsApi } from '@/features/insights/api'

describe('InsightsPage', () => {
  beforeEach(() => {
    vi.spyOn(insightsApi, 'summary').mockResolvedValue({
      headcount: 10000,
      country_count: 10,
      total_payroll_usd: 834375686,
      average_salary_usd: 83438,
      fx_rates_as_of: '2026-10-01',
    })
    vi.spyOn(insightsApi, 'countries').mockResolvedValue([
      {
        country: 'India',
        currency: 'INR',
        headcount: 2000,
        min_salary: 500000,
        max_salary: 6000000,
        average_salary: 2500000,
        median_salary: 2300000,
        average_salary_usd: 30000,
      },
    ])
    vi.spyOn(insightsApi, 'jobTitles').mockResolvedValue([
      { job_title: 'Data Analyst', currency: 'INR', headcount: 80, min_salary: 1500000, max_salary: 3000000, average_salary: 2200000 },
    ])
    vi.spyOn(insightsApi, 'departments').mockResolvedValue([
      { department: 'Engineering', headcount: 3500, total_payroll_usd: 384000000, average_salary_usd: 109860 },
    ])
  })

  it('shows org-wide headline numbers with the FX date', async () => {
    renderWithProviders(<InsightsPage />)

    expect(await screen.findByText('10,000')).toBeInTheDocument()
    expect(screen.getByText('USD 834,375,686')).toBeInTheDocument()
    expect(screen.getByText('USD 83,438')).toBeInTheDocument()
    expect(screen.getByText(/2026-10-01/)).toBeInTheDocument()
  })

  it('shows per-country stats in local currency with a USD average', async () => {
    renderWithProviders(<InsightsPage />)

    const row = await screen.findByRole('row', { name: /india/i })
    expect(within(row).getByText('INR 2,300,000')).toBeInTheDocument()
    expect(within(row).getByText('USD 30,000')).toBeInTheDocument()
  })

  it('loads job title pay for the first country by default', async () => {
    renderWithProviders(<InsightsPage />)

    await waitFor(() => expect(insightsApi.jobTitles).toHaveBeenCalledWith('India'))
    const row = await screen.findByRole('row', { name: /data analyst/i })
    expect(within(row).getByText('INR 2,200,000')).toBeInTheDocument()
  })

  it('shows department pay in USD', async () => {
    renderWithProviders(<InsightsPage />)

    const row = await screen.findByRole('row', { name: /engineering/i })
    expect(within(row).getByText('USD 109,860')).toBeInTheDocument()
  })
})
