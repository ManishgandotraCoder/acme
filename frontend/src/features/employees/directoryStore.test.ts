import { beforeEach, describe, expect, it } from 'vitest'
import { useDirectoryStore } from './directoryStore'

const state = () => useDirectoryStore.getState()

describe('directory store', () => {
  beforeEach(() => useDirectoryStore.setState(useDirectoryStore.getInitialState(), true))

  it('starts unfiltered, sorted by name, on page 1', () => {
    expect(state()).toMatchObject({ search: '', filters: {}, sort: 'full_name:asc', page: 1 })
  })

  it('goes back to page 1 whenever what is listed changes', () => {
    for (const change of [
      () => state().setSearch('ada'),
      () => state().setFilter('country', 'India'),
      () => state().setSalaryMin(50000),
      () => state().setSalaryMax(90000),
      () => state().setSort('hire_date:desc'),
    ]) {
      state().setPage(4)
      change()
      expect(state().page).toBe(1)
    }
  })

  it('clearing a filter removes it', () => {
    state().setFilter('job_level', 'Senior')
    state().setFilter('job_level', null)
    expect(state().filters.job_level).toBeUndefined()
  })

  it('sorting by a column starts in its natural direction, then toggles', () => {
    state().sortBy('annual_salary', 'desc')
    expect(state().sort).toBe('annual_salary:desc')
    state().sortBy('annual_salary', 'desc')
    expect(state().sort).toBe('annual_salary:asc')
    state().sortBy('full_name', 'asc')
    expect(state().sort).toBe('full_name:asc')
  })

  it('clear all resets filters and the salary range but keeps search and sort', () => {
    state().setSearch('ada')
    state().setSort('hire_date:desc')
    state().setFilter('country', 'India')
    state().setSalaryMin(1)
    state().clearFilters()
    expect(state()).toMatchObject({ search: 'ada', sort: 'hire_date:desc', filters: {}, salaryMin: '' })
  })
})
