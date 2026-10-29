import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { EmployeeUpdate } from '@/features/employees/types'
import { employeesApi } from '@/features/employees/api'
import type { EmployeeInput, EmployeeQuery } from '@/features/employees/types'

export const useMeta = () => useQuery({ queryKey: ['meta'], queryFn: employeesApi.meta, staleTime: 5 * 60_000 })

export const useEmployees = (query: EmployeeQuery) =>
  useQuery({
    queryKey: ['employees', query],
    queryFn: () => employeesApi.list(query),
    placeholderData: keepPreviousData, // keep the table steady while paging/filtering
  })

export const useSalaryHistory = (id: number | null) =>
  useQuery({
    queryKey: ['salary-history', id],
    queryFn: () => employeesApi.salaryHistory(id!),
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
  return useMutation({ mutationFn: (body: EmployeeInput) => employeesApi.create(body), onSuccess })
}

export function useUpdateEmployee() {
  const onSuccess = useInvalidateAfterWrite()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: EmployeeUpdate }) => employeesApi.update(id, body),
    onSuccess,
  })
}

export function useDeleteEmployee() {
  const onSuccess = useInvalidateAfterWrite()
  return useMutation({ mutationFn: (id: number) => employeesApi.remove(id), onSuccess })
}
