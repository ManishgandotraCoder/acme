import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import { useAssistantStore } from '@/features/assistant/assistantStore'
import { useDirectoryStore } from '@/features/employees/directoryStore'

afterEach(() => {
  cleanup()
  // Stores are module singletons: reset them so tests stay independent.
  useDirectoryStore.setState(useDirectoryStore.getInitialState(), true)
  useAssistantStore.setState(useAssistantStore.getInitialState(), true)
  localStorage.clear()
})

// Browser APIs Mantine relies on that jsdom does not implement.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverStub
window.HTMLElement.prototype.scrollIntoView = () => {}
window.HTMLElement.prototype.scrollTo = () => {}
