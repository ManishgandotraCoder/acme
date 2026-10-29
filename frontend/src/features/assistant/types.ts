// Mirrors backend/app/modules/assistant/schemas.py

export type AnswerKind = 'answer' | 'clarification' | 'unsupported' | 'forbidden'

export interface QueryIntent {
  metric: string
  countries: string[]
  job_titles: string[]
  departments: string[]
  statistic: 'average' | 'median'
}

export interface Column {
  key: string
  label: string
  /** usd / local: money (local uses the row's `currency`); percent: signed change. */
  format: 'text' | 'number' | 'usd' | 'local' | 'percent'
}

export interface Table {
  columns: Column[]
  rows: Record<string, unknown>[]
}

export interface Chart {
  type: 'bar'
  x: string
  y: string
  label: string
}

export interface AskResult {
  question: string
  kind: AnswerKind
  answer: string
  intent: QueryIntent
  table: Table | null
  chart: Chart | null
  scope: string | null
  suggestions: string[]
  provider: string | null
}

export interface ProviderInfo {
  id: string
  label: string
  model: string
  default: boolean
}
