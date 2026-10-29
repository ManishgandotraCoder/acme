import { screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { buildEmployee, meta } from '@/test/fixtures'
import { renderWithProviders } from '@/test/render'
import { EmployeesPage } from './EmployeesPage'
import { employeesApi } from '@/features/employees/api'
import { ApiError } from '@/shared/api/client'

const page = (items = [buildEmployee()], total = items.length) => ({
  items,
  total,
  page: 1,
  page_size: 25,
})

describe('EmployeesPage', () => {
  beforeEach(() => {
    vi.spyOn(employeesApi, 'meta').mockResolvedValue(meta)
    vi.spyOn(employeesApi, 'list').mockResolvedValue(page())
  })

  it('lists employees with salary in local currency and the total count', async () => {
    vi.spyOn(employeesApi, 'list').mockResolvedValue(page([buildEmployee()], 10000))
    renderWithProviders(<EmployeesPage />)

    const row = await screen.findByRole('row', { name: /ada lovelace/i })
    expect(within(row).getByText('GBP 80,000')).toBeInTheDocument()
    expect(screen.getByText('10,000 employees')).toBeInTheDocument()
  })

  it('shows skeleton rows while employees load', async () => {
    vi.spyOn(employeesApi, 'list').mockReturnValue(new Promise(() => {}))
    renderWithProviders(<EmployeesPage />)

    expect(await screen.findByText('Loading employees…')).toBeInTheDocument()
    expect(screen.queryByText('No employees match these filters.')).not.toBeInTheDocument()
  })

  it('searches by name after the user stops typing', async () => {
    const { user } = renderWithProviders(<EmployeesPage />)
    await screen.findByText('Ada Lovelace')

    await user.type(screen.getByPlaceholderText(/search/i), 'grace')

    await waitFor(() =>
      expect(employeesApi.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: 'grace', page: 1 }),
      ),
    )
  })

  it('deletes an employee after confirmation', async () => {
    const remove = vi.spyOn(employeesApi, 'remove').mockResolvedValue(undefined)
    const { user } = renderWithProviders(<EmployeesPage />)

    await user.click(await screen.findByRole('button', { name: /delete ada lovelace/i }))
    expect(remove).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: /^delete$/i }))

    await waitFor(() => expect(remove).toHaveBeenCalledWith(1))
  })

  it('shows salary history for an employee', async () => {
    vi.spyOn(employeesApi, 'salaryHistory').mockResolvedValue([
      {
        id: 1,
        previous_salary: 80000,
        new_salary: 88000,
        previous_currency: 'GBP',
        new_currency: 'GBP',
        reason: 'Annual review',
        changed_at: '2025-04-01T09:00:00Z',
      },
    ])
    const { user } = renderWithProviders(<EmployeesPage />)

    await user.click(await screen.findByRole('button', { name: /salary history for ada lovelace/i }))

    expect(await screen.findByText('Annual review')).toBeInTheDocument()
    expect(screen.getByText(/GBP 80,000 → GBP 88,000/)).toBeInTheDocument()
  })

  it('shows an error when employees cannot be loaded', async () => {
    vi.spyOn(employeesApi, 'list').mockRejectedValue(new ApiError(500, 'Database unavailable'))
    renderWithProviders(<EmployeesPage />)

    expect(await screen.findByText('Database unavailable')).toBeInTheDocument()
  })
})
