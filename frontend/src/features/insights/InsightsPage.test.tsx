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
      median_salary_usd: 72438,
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
        median_salary_usd: 27600,
      },
    ])
    vi.spyOn(insightsApi, 'jobTitles').mockResolvedValue([
      { job_title: 'Data Analyst', currency: 'INR', headcount: 80, min_salary: 1500000, max_salary: 3000000, average_salary: 2200000 },
    ])
    vi.spyOn(insightsApi, 'departments').mockResolvedValue([
      { department: 'Engineering', headcount: 3500, total_payroll_usd: 384000000, average_salary_usd: 109860, median_salary_usd: 100299 },
      { department: 'Sales', headcount: 1500, total_payroll_usd: 128000000, average_salary_usd: 85743, median_salary_usd: 88382 },
    ])
    vi.spyOn(insightsApi, 'levels').mockResolvedValue([
      { job_level: 'Junior', headcount: 2000, average_salary_usd: 73583, median_salary_usd: 65940, gap_to_previous_pct: null },
      { job_level: 'Mid', headcount: 3500, average_salary_usd: 77310, median_salary_usd: 69278, gap_to_previous_pct: 8.5 },
    ])
    vi.spyOn(insightsApi, 'salaryBands').mockResolvedValue([
      { label: 'Under USD 50k', min_usd: 0, max_usd: 50000, headcount: 3162 },
      { label: 'USD 50k–100k', min_usd: 50000, max_usd: 100000, headcount: 3716 },
    ])
    vi.spyOn(insightsApi, 'salaryTrends').mockResolvedValue({
      start: '2025-11-01',
      end: '2026-10-29',
      changes: 1400,
      employees: 1400,
      average_raise_pct: 4.9,
      months: [
        { month: '2026-08', changes: 714, average_raise_pct: 4.8 },
        { month: '2026-09', changes: 686, average_raise_pct: 5.0 },
      ],
    })
  })

  it('shows placeholders while insights load', async () => {
    vi.spyOn(insightsApi, 'countries').mockReturnValue(new Promise(() => {}))
    renderWithProviders(<InsightsPage />)

    expect(await screen.findByText('Loading pay by country…')).toBeInTheDocument()
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

  it('shows the org median next to the average', async () => {
    renderWithProviders(<InsightsPage />)
    expect(await screen.findByText('USD 72,438')).toBeInTheDocument()
  })

  it('shows headcount by department as a donut with a labelled legend', async () => {
    renderWithProviders(<InsightsPage />)

    const figure = await screen.findByRole('figure', { name: 'Headcount by department' })
    const engineering = await within(figure).findByRole('listitem', { name: /engineering/i })
    expect(engineering).toHaveTextContent('3,500 · 70%')
  })

  it('charts salary bands, like-for-like level gaps, and department average vs median', async () => {
    renderWithProviders(<InsightsPage />)

    expect(await screen.findByRole('figure', { name: 'Employees by salary band (USD)' })).toBeInTheDocument()
    const levels = await screen.findByRole('figure', { name: 'Pay vs the level below' })
    expect(within(levels).getByText(/same job title and country/i)).toBeInTheDocument()
    expect(await screen.findByRole('figure', { name: 'Average vs median salary by department (USD)' })).toBeInTheDocument()
  })

  it('shows salary trends as two charts, not one with two scales', async () => {
    renderWithProviders(<InsightsPage />)

    const changes = await screen.findByRole('figure', { name: 'Salary changes per month' })
    expect(await within(changes).findByText(/1,400 changes/)).toBeInTheDocument()
    const raises = screen.getByRole('figure', { name: 'Average raise per month (%)' })
    expect(within(raises).getByText(/4.9% on average/)).toBeInTheDocument()
  })
})
