import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { employeesApi } from '@/features/employees/api'
import { insightsApi } from '@/features/insights/api'
import { buildEmployee, meta } from '@/test/fixtures'
import { renderWithProviders } from '@/test/render'
import { App } from './App'

describe('App navigation', () => {
  beforeEach(() => {
    vi.spyOn(employeesApi, 'meta').mockResolvedValue(meta)
    vi.spyOn(employeesApi, 'list').mockResolvedValue({ items: [buildEmployee()], total: 1, page: 1, page_size: 25 })
    vi.spyOn(insightsApi, 'summary').mockReturnValue(new Promise(() => {}))
    vi.spyOn(insightsApi, 'countries').mockReturnValue(new Promise(() => {}))
    vi.spyOn(insightsApi, 'departments').mockReturnValue(new Promise(() => {}))
  })

  it('home is the employee directory, with no sidebar', async () => {
    renderWithProviders(<App />, { route: '/' })

    expect(await screen.findByRole('heading', { name: 'Employees' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('home links to pay insights, and insights links back', async () => {
    const { user } = renderWithProviders(<App />, { route: '/' })

    await user.click(await screen.findByRole('link', { name: /pay insights/i }))
    expect(await screen.findByRole('heading', { name: 'Pay insights' })).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /back to employees/i }))
    expect(await screen.findByRole('heading', { name: 'Employees' })).toBeInTheDocument()
  })

  it('offers the pay assistant on every page', async () => {
    renderWithProviders(<App />, { route: '/insights' })
    expect(await screen.findByRole('button', { name: /open pay assistant/i })).toBeInTheDocument()
  })

  it('old /ask links land on home with the assistant open', async () => {
    renderWithProviders(<App />, { route: '/ask' })
    expect(await screen.findByRole('dialog', { name: /pay assistant/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Employees' })).toBeInTheDocument()
  })
})
