import { beforeEach, describe, expect, it, vi } from 'vitest'
import { reloadAssistant as reload } from '@/test/stores'
import { useAssistantStore } from './assistantStore'

const state = () => useAssistantStore.getState()

describe('assistant store', () => {
  beforeEach(async () => {
    localStorage.clear()
    await reload()
  })

  it('numbers messages in order', () => {
    state().append({ role: 'user', text: 'a' })
    state().append({ role: 'user', text: 'b' })
    expect(state().messages.map((m) => m.id)).toEqual([0, 1])
  })

  it('keeps the conversation and the chosen model across a reload, but not open/closed', async () => {
    state().open()
    state().append({ role: 'user', text: 'Average pay?' })
    state().chooseProvider('openai')

    await reload()

    expect(state().messages).toEqual([{ id: 0, role: 'user', text: 'Average pay?' }])
    expect(state().provider).toBe('openai')
    expect(state().isOpen).toBe(false)
  })

  it('keeps only the last 50 messages', async () => {
    for (let i = 0; i < 60; i++) state().append({ role: 'user', text: `q${i}` })
    await reload()
    expect(state().messages).toHaveLength(50)
    expect(state().messages[0]).toMatchObject({ text: 'q10' })
  })

  it('new conversation erases the saved copy too', async () => {
    state().append({ role: 'user', text: 'Who earns most?' })
    state().newConversation()
    await reload()
    expect(state().messages).toEqual([])
  })

  it('works, unsaved, when the browser blocks storage', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(() => state().append({ role: 'user', text: 'a' })).not.toThrow()
    expect(state().messages).toHaveLength(1)
  })
})
