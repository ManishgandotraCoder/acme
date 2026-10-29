import { request } from '@/shared/api/client'
import type { AskResult } from './types'

export const assistantApi = {
  ask: (question: string) => request<AskResult>('/api/ask', { method: 'POST', body: { question } }),
}
