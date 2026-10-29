// Mirrors backend/app/modules/assistant/schemas.py

export interface AskResult {
  question: string
  answer: string
  intent: {
    metric: string
    country: string | null
    job_title: string | null
    department: string | null
  }
  data: Record<string, unknown>[]
}
