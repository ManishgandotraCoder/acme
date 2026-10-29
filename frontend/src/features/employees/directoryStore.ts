import { create } from 'zustand'
import type { EmployeeQuery } from '@/features/employees/types'
import { SORT_OPTIONS, type Amount, type Filters } from './components/directoryOptions'

/**
 * What the employee directory is showing: search, filters, salary range, sort and page.
 * Client state only (the employees themselves are server state, in TanStack Query); kept in a
 * store so it survives leaving the page and coming back.
 */
interface DirectoryState {
  search: string
  filters: Filters
  salaryMin: Amount
  salaryMax: Amount
  sort: string // "field:order", one of SORT_OPTIONS
  page: number
  setSearch: (search: string) => void
  setFilter: (key: keyof Filters, value: string | null) => void
  setSalaryMin: (value: Amount) => void
  setSalaryMax: (value: Amount) => void
  setSort: (sort: string) => void
  /** Column-header click: sort by that field in its natural direction, or flip it. */
  sortBy: (field: EmployeeQuery['sort'], firstOrder: EmployeeQuery['order']) => void
  setPage: (page: number) => void
  /** Filters and salary range only; search and sort stay. */
  clearFilters: () => void
}

export const useDirectoryStore = create<DirectoryState>()((set) => ({
  search: '',
  filters: {},
  salaryMin: '',
  salaryMax: '',
  sort: SORT_OPTIONS[0].value,
  page: 1,
  // Anything that changes what is listed goes back to page 1.
  setSearch: (search) => set({ search, page: 1 }),
  setFilter: (key, value) => set((s) => ({ filters: { ...s.filters, [key]: value ?? undefined }, page: 1 })),
  setSalaryMin: (salaryMin) => set({ salaryMin, page: 1 }),
  setSalaryMax: (salaryMax) => set({ salaryMax, page: 1 }),
  setSort: (sort) => set({ sort, page: 1 }),
  sortBy: (field, firstOrder) =>
    set((s) => {
      const [current, order] = s.sort.split(':')
      const next = current === field ? (order === 'asc' ? 'desc' : 'asc') : firstOrder
      return { sort: `${field}:${next}`, page: 1 }
    }),
  setPage: (page) => set({ page }),
  clearFilters: () => set({ filters: {}, salaryMin: '', salaryMax: '', page: 1 }),
}))
