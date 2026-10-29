import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { EmployeeInput, EmployeeQuery, EmployeeUpdate } from '../../api'

export const useMeta = () => useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: 5 * 60_000 })

export const useEmployees = (query: EmployeeQuery) =>
  useQuery({
    queryKey: ['employees', query],
    queryFn: () => api.listEmployees(query),
    placeholderData: keepPreviousData, // keep the table steady while paging/filtering
  })

export const useSalaryHistory = (id: number | null) =>
  useQuery({
    queryKey: ['salary-history', id],
    queryFn: () => api.salaryHistory(id!),
    enabled: id !== null,
  })

/** Any write can change lists, dropdown values and insights, so refresh all of them. */
function useInvalidateAfterWrite() {
  const client = useQueryClient()
  return () =>
    Promise.all(
      ['employees', 'meta', 'insights', 'salary-history'].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    )
}

export function useCreateEmployee() {
  const onSuccess = useInvalidateAfterWrite()
  return useMutation({ mutationFn: (body: EmployeeInput) => api.createEmployee(body), onSuccess })
}

export function useUpdateEmployee() {
  const onSuccess = useInvalidateAfterWrite()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: EmployeeUpdate }) => api.updateEmployee(id, body),
    onSuccess,
  })
}

export function useDeleteEmployee() {
  const onSuccess = useInvalidateAfterWrite()
  return useMutation({ mutationFn: (id: number) => api.deleteEmployee(id), onSuccess })
}
