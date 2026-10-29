import { request } from '@/shared/api/client'
import type { AskResult, ProviderInfo } from './types'

export const assistantApi = {
  providers: () => request<ProviderInfo[]>('/api/assistant/providers'),
  ask: (question: string, provider?: string) =>
    request<AskResult>('/api/ask', { method: 'POST', body: { question, provider } }),
}
