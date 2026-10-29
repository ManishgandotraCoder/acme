import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { assistantApi } from '@/features/assistant/api'
import { ApiError } from '@/shared/api/client'
import { renderWithProviders } from '@/test/render'
import { ChatWidget } from './ChatWidget'
import type { AskResult } from './types'

const answer: AskResult = {
  question: 'What do data analysts earn in Germany?',
  kind: 'answer',
  answer: 'Data Analyst in Germany: 38 employees, average EUR 65,974.',
  intent: {
    metric: 'job_title_stats',
    countries: ['Germany'],
    job_titles: ['Data Analyst'],
    departments: [],
    statistic: 'average',
  },
  table: null,
  chart: null,
  scope: 'Data Analyst · Germany · EUR',
  suggestions: [],
  provider: null,
}

async function openChat() {
  const utils = renderWithProviders(<ChatWidget />)
  await utils.user.click(screen.getByRole('button', { name: /open pay assistant/i }))
  return { ...utils, chat: screen.getByRole('dialog', { name: /pay assistant/i }) }
}

const departments: AskResult = {
  ...answer,
  question: 'Which department has the highest median salary?',
  answer:
    'Engineering has the highest median salary (USD 100,299). Median salary by department (USD): Engineering 100,299; Sales 88,382.',
  intent: { ...answer.intent, metric: 'department_stats', countries: [], job_titles: [], statistic: 'median' },
  table: {
    columns: [
      { key: 'department', label: 'Department', format: 'text' },
      { key: 'headcount', label: 'Employees', format: 'number' },
      { key: 'median_salary_usd', label: 'Median salary', format: 'usd' },
      { key: 'average_salary', label: 'Average (local)', format: 'local' },
      { key: 'gap', label: 'Gap', format: 'percent' },
    ],
    rows: [
      { department: 'Engineering', headcount: 3519, median_salary_usd: 100299, average_salary: 95000, currency: 'EUR', gap: 8.5 },
      { department: 'Sales', headcount: 1800, median_salary_usd: 88382, average_salary: 81000, currency: 'EUR', gap: 2.1 },
      { department: 'Finance', headcount: 2, median_salary_usd: null, average_salary: null, currency: 'EUR', gap: null },
    ],
  },
  chart: { type: 'bar', x: 'department', y: 'median_salary_usd', label: 'Median salary (USD)' },
  scope: 'All employees · USD converted at fixed FX rates as of 2026-10-01',
  provider: 'ollama',
}

const providers = [
  { id: 'ollama', label: 'Ollama (local)', model: 'llama3.2', default: true },
  { id: 'openai', label: 'OpenAI', model: 'gpt-test', default: false },
]

describe('ChatWidget', () => {
  beforeEach(() => {
    vi.spyOn(assistantApi, 'providers').mockResolvedValue([providers[0]])
  })

  it('is a closed launcher until clicked', async () => {
    const { user } = renderWithProviders(<ChatWidget />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /open pay assistant/i }))
    const chat = screen.getByRole('dialog', { name: /pay assistant/i })
    expect(within(chat).getByLabelText(/message/i)).toBeInTheDocument()
  })

  it('chats: shows the question, then the grounded answer with its interpretation', async () => {
    const ask = vi.spyOn(assistantApi, 'ask').mockResolvedValue(answer)
    const { user, chat } = await openChat()

    await user.type(within(chat).getByLabelText(/message/i), 'What do data analysts earn in Germany?{Enter}')

    expect(ask).toHaveBeenCalledWith('What do data analysts earn in Germany?', 'ollama')
    expect(within(chat).getByText('What do data analysts earn in Germany?')).toBeInTheDocument()
    expect(await within(chat).findByText(answer.answer)).toBeInTheDocument()
    expect(within(chat).getByText('Country: Germany')).toBeInTheDocument()
    expect(within(chat).getByLabelText(/message/i)).toHaveValue('')
  })

  it('shows a typing indicator while the model works', async () => {
    vi.spyOn(assistantApi, 'ask').mockReturnValue(new Promise(() => {}))
    const { user, chat } = await openChat()

    await user.type(within(chat).getByLabelText(/message/i), 'Average pay?{Enter}')

    expect(await within(chat).findByText('Thinking…')).toBeInTheDocument()
    expect(within(chat).getByRole('button', { name: /send/i })).toBeDisabled()
  })

  it('offers example questions that send with one click', async () => {
    const ask = vi.spyOn(assistantApi, 'ask').mockResolvedValue(answer)
    const { user, chat } = await openChat()

    await user.click(within(chat).getByRole('button', { name: /which department has the highest median salary/i }))

    expect(ask).toHaveBeenCalledWith('Which department has the highest median salary?', 'ollama')
  })

  it('explains in the conversation when the assistant is unavailable', async () => {
    vi.spyOn(assistantApi, 'ask').mockRejectedValue(
      new ApiError(503, 'The AI assistant is unavailable right now. Is Ollama running?'),
    )
    const { user, chat } = await openChat()

    await user.type(within(chat).getByLabelText(/message/i), 'Average pay?{Enter}')

    expect(await within(chat).findByText(/Is Ollama running\?/)).toBeInTheDocument()
  })

  it('does not send an empty message', async () => {
    const ask = vi.spyOn(assistantApi, 'ask')
    const { chat } = await openChat()
    expect(within(chat).getByRole('button', { name: /send/i })).toBeDisabled()
    expect(ask).not.toHaveBeenCalled()
  })

  it('keeps the conversation when closed and reopened', async () => {
    vi.spyOn(assistantApi, 'ask').mockResolvedValue(answer)
    const { user, chat } = await openChat()
    await user.type(within(chat).getByLabelText(/message/i), 'Analysts in Germany?{Enter}')
    await within(chat).findByText(answer.answer)

    await user.click(within(chat).getByRole('button', { name: /close/i }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /open pay assistant/i }))

    expect(screen.getByText(answer.answer)).toBeInTheDocument()
  })

  it('shows the evidence: a chart, a formatted table and the data scope', async () => {
    vi.spyOn(assistantApi, 'ask').mockResolvedValue(departments)
    const { user, chat } = await openChat()

    await user.type(within(chat).getByLabelText(/message/i), 'Highest median?{Enter}')

    expect(await within(chat).findByText('Engineering has the highest median salary (USD 100,299).')).toBeInTheDocument()
    expect(within(chat).getByLabelText('Chart: Median salary (USD)')).toBeInTheDocument()
    const engineering = within(chat).getByRole('row', { name: /engineering/i })
    expect(within(engineering).getByText('USD 100,299')).toBeInTheDocument()
    expect(within(engineering).getByText('EUR 95,000')).toBeInTheDocument()
    expect(within(engineering).getByText('+8.5%')).toBeInTheDocument()
    expect(within(engineering).getByText('3,519')).toBeInTheDocument()
    const finance = within(chat).getByRole('row', { name: /finance/i })
    expect(within(finance).getAllByText('—')).toHaveLength(3) // hidden for privacy
    expect(within(chat).getByText(/fixed FX rates as of 2026-10-01/)).toBeInTheDocument()
  })

  it('asks a clarifying question whose options send with one click', async () => {
    const ask = vi.spyOn(assistantApi, 'ask').mockResolvedValueOnce({
      ...answer,
      kind: 'clarification',
      answer: 'Which role do you mean: QA Engineer or Software Engineer?',
      suggestions: ['What do QA Engineers earn?', 'What do Software Engineers earn?'],
    })
    const { user, chat } = await openChat()
    await user.type(within(chat).getByLabelText(/message/i), 'What do engineers make?{Enter}')

    // The model's guesses aren't what the answer used, so they aren't shown as its interpretation.
    expect(await within(chat).findByText(/Which role do you mean/)).toBeInTheDocument()
    expect(within(chat).queryByText(/Job title:/)).not.toBeInTheDocument()

    await user.click(await within(chat).findByRole('button', { name: 'What do QA Engineers earn?' }))

    expect(ask).toHaveBeenLastCalledWith('What do QA Engineers earn?', 'ollama')
  })

  it('explains when individual pay is not visible to this user', async () => {
    vi.spyOn(assistantApi, 'ask').mockResolvedValue({
      ...answer,
      kind: 'forbidden',
      answer: "You don't have permission to see individual employees' pay, so I can't list people.",
      suggestions: ['What is the salary gap between job levels?'],
    })
    const { user, chat } = await openChat()
    await user.type(within(chat).getByLabelText(/message/i), 'Who are the outliers?{Enter}')

    expect(await within(chat).findByText(/don't have permission/)).toBeInTheDocument()
    expect(within(chat).getByRole('button', { name: 'What is the salary gap between job levels?' })).toBeInTheDocument()
  })

  it('lets the user pick a model when more than one is configured', async () => {
    vi.spyOn(assistantApi, 'providers').mockResolvedValue(providers)
    const ask = vi.spyOn(assistantApi, 'ask').mockResolvedValue({ ...answer, provider: 'openai' })
    const { user, chat } = await openChat()

    await user.click(await within(chat).findByRole('textbox', { name: /model/i }))
    await user.click(screen.getByRole('option', { name: /OpenAI/ }))
    await user.type(within(chat).getByLabelText(/message/i), 'Average pay?{Enter}')

    expect(ask).toHaveBeenCalledWith('Average pay?', 'openai')
    expect(await within(chat).findByText('via OpenAI')).toBeInTheDocument()
  })

  it('hides the model picker when only one model is available', async () => {
    const { chat } = await openChat()
    await screen.findByRole('dialog')
    expect(within(chat).queryByRole('textbox', { name: /model/i })).not.toBeInTheDocument()
  })
})
