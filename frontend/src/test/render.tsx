import { MantineProvider } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { theme } from '@/app/theme'

/** Render with the same providers the app uses; retries off so failures surface immediately. */
export function renderWithProviders(ui: ReactElement, { route = '/' }: { route?: string } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return {
    user: userEvent.setup(),
    ...render(
      <QueryClientProvider client={queryClient}>
        <MantineProvider theme={theme} env="test">
          <Notifications />
          <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
        </MantineProvider>
      </QueryClientProvider>,
    ),
  }
}
