import { useAssistantStore } from '@/features/assistant/assistantStore'

/** What a page reload does to the assistant: memory is gone, the saved copy is read back. */
export async function reloadAssistant(): Promise<void> {
  const { name } = useAssistantStore.persist.getOptions()
  const saved = localStorage.getItem(name!)
  // Resetting memory goes through persist, which would overwrite the saved copy.
  useAssistantStore.setState(useAssistantStore.getInitialState(), true)
  if (saved === null) localStorage.removeItem(name!)
  else localStorage.setItem(name!, saved)
  await useAssistantStore.persist.rehydrate()
}
