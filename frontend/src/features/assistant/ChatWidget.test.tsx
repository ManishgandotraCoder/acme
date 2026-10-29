import { screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
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

describe('ChatWidget', () => {
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

    expect(ask).toHaveBeenCalledWith('What do data analysts earn in Germany?')
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

    await user.click(within(chat).getByRole('button', { name: /which department has the highest average pay/i }))

    expect(ask).toHaveBeenCalledWith('Which department has the highest average pay?')
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
})
