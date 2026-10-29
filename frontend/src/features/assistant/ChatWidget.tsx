import {
  ActionIcon,
  Badge,
  Box,
  Button,
  List,
  CloseButton,
  Group,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Text,
  Textarea,
  ThemeIcon,
  Tooltip,
  Transition,
} from '@mantine/core'
import {
  IconAlertTriangle,
  IconInfoCircle,
  IconLock,
  IconMessageChatbot,
  IconRefresh,
  IconSend2,
  IconSparkles,
} from '@tabler/icons-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { assistantApi } from '@/features/assistant/api'
import type { AskResult } from '@/features/assistant/types'
import { toAnswerParts } from './answerFormat'
import { WorkingIndicator } from '@/shared/ui/loading'

// Charts are heavy and the chat is on every page: load them with the first answer that has one.
const AnswerEvidence = lazy(() => import('./AnswerEvidence').then((m) => ({ default: m.AnswerEvidence })))

const EXAMPLES = [
  'What are the average and median salaries across the organization?',
  'Which department has the highest median salary?',
  'Compare average salaries across countries',
  'What is the salary gap between job levels?',
  'Which employees earn significantly more or less than peers?',
  'How have salaries changed over the last 12 months?',
]

const METRIC_LABELS: Record<string, string> = {
  org_summary: 'Org summary',
  country_stats: 'Country stats',
  job_title_stats: 'Job title stats',
  department_stats: 'Department stats',
  level_stats: 'Pay by level',
  salary_bands: 'Salary bands',
  outliers: 'Outliers',
  above_department_average: 'Above department average',
  salary_trends: 'Salary trends',
  unsupported: 'Not understood',
}

type Message =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'assistant'; result: AskResult }
  | { id: number; role: 'error'; text: string }

type NewMessage = Message extends infer M ? (M extends Message ? Omit<M, 'id'> : never) : never

/** Location state that opens the assistant on arrival (used by the old /ask route). */
export interface OpenAssistantState {
  openAssistant?: boolean
}

/**
 * Floating pay assistant. Mounted once in the app shell, so the conversation survives
 * navigation between pages.
 */
export function ChatWidget() {
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const nextId = useRef(0)
  const viewport = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)

  const append = (message: NewMessage) =>
    setMessages((previous) => [...previous, { ...message, id: nextId.current++ }])

  const providers = useQuery({ queryKey: ['assistant', 'providers'], queryFn: assistantApi.providers })
  const [chosenProvider, setChosenProvider] = useState<string | null>(null)
  const provider = chosenProvider ?? providers.data?.find((p) => p.default)?.id
  const providerLabel = (id: string | null) => providers.data?.find((p) => p.id === id)?.label ?? id

  const ask = useMutation({
    mutationFn: (question: string) => assistantApi.ask(question, provider),
    onSuccess: (result) => append({ role: 'assistant', result }),
    onError: (error) =>
      append({ role: 'error', text: `${error.message} Pay insights still work without the assistant.` }),
  })

  useEffect(() => {
    if ((location.state as OpenAssistantState | null)?.openAssistant) setOpen(true)
  }, [location.state])

  // Keep the latest message in view.
  useEffect(() => {
    viewport.current?.scrollTo({ top: viewport.current.scrollHeight, behavior: 'smooth' })
  }, [messages, ask.isPending])

  useEffect(() => {
    if (open) input.current?.focus()
  }, [open])

  const send = (text: string) => {
    const question = text.trim()
    if (!question || ask.isPending) return
    append({ role: 'user', text: question })
    setDraft('')
    ask.mutate(question)
  }

  return (
    <>
      {!open && (
        <Tooltip label="Ask about pay" position="left">
          <ActionIcon
            size={56}
            radius="xl"
            variant="filled"
            aria-label="Open pay assistant"
            onClick={() => setOpen(true)}
            style={{ position: 'fixed', right: 24, bottom: 24, zIndex: 200, boxShadow: 'var(--mantine-shadow-lg)' }}
          >
            <IconMessageChatbot size={28} />
          </ActionIcon>
        </Tooltip>
      )}

      <Transition mounted={open} transition="pop-bottom-right" duration={180}>
        {(styles) => (
          <Paper
            role="dialog"
            aria-label="Pay assistant"
            shadow="xl"
            radius="lg"
            withBorder
            onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
            style={{
              ...styles,
              position: 'fixed',
              right: 'max(16px, min(24px, 3vw))',
              bottom: 'max(16px, min(24px, 3vw))',
              width: 'min(480px, calc(100vw - 32px))',
              height: 'min(680px, calc(100dvh - 32px))',
              zIndex: 200,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <Group justify="space-between" px="md" py="sm" bg="var(--mantine-primary-color-filled)" c="white" wrap="nowrap">
              <Group gap="sm" wrap="nowrap">
                <ThemeIcon variant="white" radius="xl" size="lg">
                  <IconSparkles size={18} />
                </ThemeIcon>
                <div>
                  <Text fw={600} lh={1.2}>
                    Pay assistant
                  </Text>
                  <Text size="xs" opacity={0.85}>
                    Answers come from your salary data
                  </Text>
                </div>
              </Group>
              <Group gap={4} wrap="nowrap">
                {messages.length > 0 && (
                  <Tooltip label="New conversation">
                    <ActionIcon variant="subtle" color="white" aria-label="New conversation" onClick={() => setMessages([])}>
                      <IconRefresh size={18} />
                    </ActionIcon>
                  </Tooltip>
                )}
                <CloseButton variant="subtle" c="white" aria-label="Close" onClick={() => setOpen(false)} />
              </Group>
            </Group>

            <ScrollArea flex={1} viewportRef={viewport} px="md" py="sm">
              <Stack gap="sm" pb="xs">
                <Bubble from="assistant">
                  Hi! Ask me how ACME pays people: averages and medians, departments, countries, levels,
                  outliers, salary bands or trends. I look the numbers up in the salary database.
                </Bubble>
                {messages.length === 0 && (
                  <Stack gap={6} align="flex-start">
                    {EXAMPLES.map((example) => (
                      <SuggestionButton key={example} onClick={() => send(example)}>
                        {example}
                      </SuggestionButton>
                    ))}
                  </Stack>
                )}
                {messages.map((m) => {
                  if (m.role === 'user') return <Bubble key={m.id} from="user">{m.text}</Bubble>
                  if (m.role === 'error')
                    return (
                      <Bubble key={m.id} from="error">
                        <Group gap={6} wrap="nowrap" align="flex-start">
                          <IconAlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                          <span>{m.text}</span>
                        </Group>
                      </Bubble>
                    )
                  const { answer, intent, kind, table, suggestions } = m.result
                  return (
                    <Bubble key={m.id} from="assistant" wide={table !== null}>
                      {kind === 'forbidden' ? (
                        <Group gap={6} wrap="nowrap" align="flex-start">
                          <IconLock size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                          <span>{answer}</span>
                        </Group>
                      ) : (
                        <AnswerText answer={answer} hasTable={table !== null} />
                      )}
                      <Suspense fallback={null}>
                        <AnswerEvidence result={m.result} />
                      </Suspense>
                      {suggestions.length > 0 && (
                        <Stack gap={4} mt={8} align="flex-start">
                          {suggestions.map((suggestion) => (
                            <SuggestionButton key={suggestion} onClick={() => send(suggestion)}>
                              {suggestion}
                            </SuggestionButton>
                          ))}
                        </Stack>
                      )}
                      {m.result.scope && (
                        <Group gap={4} mt={8} wrap="nowrap" align="flex-start" c="dimmed">
                          <IconInfoCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                          <Text size="xs">{m.result.scope}</Text>
                        </Group>
                      )}
                      <Group gap={4} mt={8}>
                        {/* How the question was understood; only an answer actually used it. */}
                        {kind === 'answer' && (
                          <>
                            <IntentBadge variant="light">{METRIC_LABELS[intent.metric] ?? intent.metric}</IntentBadge>
                            {intent.countries.map((c) => (
                              <IntentBadge key={c}>Country: {c}</IntentBadge>
                            ))}
                            {intent.job_titles.map((t) => (
                              <IntentBadge key={t}>Job title: {t}</IntentBadge>
                            ))}
                            {intent.departments.map((d) => (
                              <IntentBadge key={d}>Department: {d}</IntentBadge>
                            ))}
                          </>
                        )}
                        {m.result.provider && <IntentBadge>via {providerLabel(m.result.provider)}</IntentBadge>}
                      </Group>
                    </Bubble>
                  )
                })}
                {ask.isPending && (
                  <Bubble from="assistant">
                    <WorkingIndicator label="Thinking…" />
                  </Bubble>
                )}
              </Stack>
            </ScrollArea>

            <Box
              component="form"
              px="md"
              pt="xs"
              pb="sm"
              style={{ borderTop: '1px solid var(--mantine-color-default-border)' }}
              onSubmit={(e) => {
                e.preventDefault()
                send(draft)
              }}
            >
              {(providers.data?.length ?? 0) > 1 && (
                <Select
                  aria-label="Model"
                  size="xs"
                  mb={6}
                  w={200}
                  allowDeselect={false}
                  data={providers.data!.map((p) => ({ value: p.id, label: `${p.label} · ${p.model}` }))}
                  value={provider ?? null}
                  onChange={setChosenProvider}
                  comboboxProps={{ withinPortal: false }}
                />
              )}
              <Group gap="xs" align="flex-end" wrap="nowrap">
                <Textarea
                  ref={input}
                  aria-label="Message"
                  placeholder="Ask about pay…"
                  autosize
                  minRows={1}
                  maxRows={4}
                  maxLength={500}
                  radius="xl"
                  flex={1}
                  value={draft}
                  onChange={(e) => setDraft(e.currentTarget.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      send(draft)
                    }
                  }}
                />
                <ActionIcon type="submit" size={36} radius="xl" aria-label="Send" disabled={!draft.trim() || ask.isPending}>
                  <IconSend2 size={18} />
                </ActionIcon>
              </Group>
              <Text size="xs" c="dimmed" ta="center" mt={6}>
                The AI only interprets your question. Every number comes from the database.
              </Text>
            </Box>
          </Paper>
        )}
      </Transition>
    </>
  )
}

/** Answer text; a list the table below already shows is reduced to its lead sentence. */
function AnswerText({ answer, hasTable }: { answer: string; hasTable: boolean }) {
  const parts = toAnswerParts(answer)
  if ('text' in parts) return <>{parts.text}</>
  if (hasTable) return <>{parts.lead ?? `${parts.title}:`}</>
  return (
    <>
      {parts.lead && <Text size="sm">{parts.lead}</Text>}
      {parts.title}
      <List size="sm" spacing={2} mt={4}>
        {parts.items.map((item) => (
          <List.Item key={item}>{item}</List.Item>
        ))}
      </List>
    </>
  )
}

function SuggestionButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <Button
      variant="light"
      size="xs"
      radius="xl"
      h="auto"
      py={6}
      fw={500}
      styles={{ label: { whiteSpace: 'normal', textAlign: 'left' } }}
      onClick={onClick}
    >
      {children}
    </Button>
  )
}

function IntentBadge({ children, variant = 'outline' }: { children: ReactNode; variant?: 'light' | 'outline' }) {
  return (
    <Badge size="sm" variant={variant} tt="none" fw={500}>
      {children}
    </Badge>
  )
}

const BUBBLE_STYLES = {
  user: { bg: 'var(--mantine-primary-color-filled)', c: 'white', align: 'flex-end', corner: 'borderBottomRightRadius' },
  assistant: { bg: 'var(--mantine-color-gray-light)', c: undefined, align: 'flex-start', corner: 'borderBottomLeftRadius' },
  error: { bg: 'var(--mantine-color-red-light)', c: 'var(--mantine-color-red-light-color)', align: 'flex-start', corner: 'borderBottomLeftRadius' },
} as const

function Bubble({ from, wide, children }: { from: keyof typeof BUBBLE_STYLES; wide?: boolean; children: ReactNode }) {
  const s = BUBBLE_STYLES[from]
  return (
    <Box
      bg={s.bg}
      c={s.c}
      px="sm"
      py={8}
      maw={wide ? '100%' : '85%'}
      w={wide ? '100%' : undefined}
      style={{ alignSelf: s.align, borderRadius: 16, [s.corner]: 4, fontSize: 'var(--mantine-font-size-sm)', lineHeight: 1.45 }}
    >
      {children}
    </Box>
  )
}
