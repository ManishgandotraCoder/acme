import { create } from 'zustand'
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware'
import type { AskResult } from './types'

export type Message =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'assistant'; result: AskResult }
  | { id: number; role: 'error'; text: string }

type NewMessage = Message extends infer M ? (M extends Message ? Omit<M, 'id'> : never) : never

const MAX_SAVED_MESSAGES = 50

interface AssistantState {
  isOpen: boolean
  messages: Message[]
  /** The model chosen in the chat; null = the server's default. */
  provider: string | null
  open: () => void
  close: () => void
  append: (message: NewMessage) => void
  /** Clears the conversation, including the copy saved in this browser. */
  newConversation: () => void
  chooseProvider: (provider: string) => void
}

/**
 * localStorage that never throws: blocked or full storage means the chat simply isn't saved.
 * Answers can name individuals' pay, so the saved copy is per browser and erased by
 * "New conversation".
 */
const safeLocalStorage: StateStorage = {
  getItem: (name) => {
    try {
      return localStorage.getItem(name)
    } catch {
      return null
    }
  },
  setItem: (name, value) => {
    try {
      localStorage.setItem(name, value)
    } catch {
      // not saved
    }
  },
  removeItem: (name) => {
    try {
      localStorage.removeItem(name)
    } catch {
      // nothing to remove
    }
  },
}

export const useAssistantStore = create<AssistantState>()(
  persist(
    (set) => ({
      isOpen: false,
      messages: [],
      provider: null,
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),
      append: (message) =>
        set((s) => {
          const id = s.messages.length ? s.messages[s.messages.length - 1].id + 1 : 0
          return { messages: [...s.messages, { ...message, id } as Message] }
        }),
      newConversation: () => set({ messages: [] }),
      chooseProvider: (provider) => set({ provider }),
    }),
    {
      name: 'pay-assistant',
      version: 1,
      storage: createJSONStorage(() => safeLocalStorage),
      // Open/closed is per visit; the conversation and the model choice are kept.
      partialize: (s) => ({ messages: s.messages.slice(-MAX_SAVED_MESSAGES), provider: s.provider }),
    },
  ),
)
