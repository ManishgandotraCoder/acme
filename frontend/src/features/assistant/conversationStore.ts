/**
 * Keeps the pay-assistant conversation in this browser (localStorage), so it survives a reload.
 * Per viewer and best-effort: storage may be blocked or full, and then the chat simply isn't
 * saved. Answers can name individual employees' pay, so "New conversation" erases it.
 */
const KEY = 'pay-assistant:conversation:v1'
const MAX_MESSAGES = 50

export function loadConversation<T>(): T[] {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

export function saveConversation<T>(messages: T[]): void {
  try {
    if (messages.length === 0) localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, JSON.stringify(messages.slice(-MAX_MESSAGES)))
  } catch {
    // Storage blocked or full: the conversation just isn't kept.
  }
}
