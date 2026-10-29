import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '../../api'
import { renderWithProviders } from '../../test/render'
import { AskPage } from './AskPage'

const result = {
  question: 'What do data analysts earn in Germany?',
  answer: 'Data Analyst in Germany: 38 employees, average EUR 65,974.',
  intent: { metric: 'job_title_stats', country: 'Germany', job_title: 'Data Analyst', department: null },
  data: [],
}

describe('AskPage', () => {
  it('answers a typed question and shows how it was interpreted', async () => {
    const ask = vi.spyOn(api, 'ask').mockResolvedValue(result)
    const { user } = renderWithProviders(<AskPage />)

    await user.type(screen.getByLabelText(/your question/i), 'What do data analysts earn in Germany?')
    await user.click(screen.getByRole('button', { name: /ask/i }))

    expect(ask).toHaveBeenCalledWith('What do data analysts earn in Germany?')
    expect(await screen.findByText(result.answer)).toBeInTheDocument()
    expect(screen.getByText('Country: Germany')).toBeInTheDocument()
    expect(screen.getByText('Job title: Data Analyst')).toBeInTheDocument()
  })

  it('lets the user ask an example question with one click', async () => {
    const ask = vi.spyOn(api, 'ask').mockResolvedValue(result)
    const { user } = renderWithProviders(<AskPage />)

    await user.click(screen.getByRole('button', { name: /which department has the highest average pay/i }))

    expect(ask).toHaveBeenCalledWith('Which department has the highest average pay?')
  })

  it('explains when the AI assistant is unavailable', async () => {
    vi.spyOn(api, 'ask').mockRejectedValue(
      new ApiError(503, 'The AI assistant is unavailable right now. Is Ollama running?'),
    )
    const { user } = renderWithProviders(<AskPage />)

    await user.type(screen.getByLabelText(/your question/i), 'Average pay?')
    await user.click(screen.getByRole('button', { name: /ask/i }))

    expect(await screen.findByText(/Is Ollama running\?/)).toBeInTheDocument()
    expect(screen.getByText(/Pay insights page still works/i)).toBeInTheDocument()
  })

  it('does not submit an empty question', async () => {
    const ask = vi.spyOn(api, 'ask')
    renderWithProviders(<AskPage />)
    expect(screen.getByRole('button', { name: /ask/i })).toBeDisabled()
    expect(ask).not.toHaveBeenCalled()
  })
})
