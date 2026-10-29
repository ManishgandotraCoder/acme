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
  Stack,
  Text,
  Textarea,
  ThemeIcon,
  Tooltip,
  Transition,
} from '@mantine/core'
import { IconAlertTriangle, IconMessageChatbot, IconRefresh, IconSend2, IconSparkles } from '@tabler/icons-react'
import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { assistantApi } from '@/features/assistant/api'
import type { AskResult } from '@/features/assistant/types'
import { toAnswerParts } from './answerFormat'
import { WorkingIndicator } from '@/shared/ui/loading'

const EXAMPLES = [
  'What do software engineers earn in India?',
  'Which department has the highest average pay?',
  'Compare product manager salaries across countries',
  'Give me pay statistics for Japan',
]

const METRIC_LABELS: Record<string, string> = {
  org_summary: 'Org summary',
  country_stats: 'Country stats',
  job_title_stats: 'Job title stats',
  department_stats: 'Department stats',
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

  const ask = useMutation({
    mutationFn: (question: string) => assistantApi.ask(question),
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
              width: 'min(400px, calc(100vw - 32px))',
              height: 'min(600px, calc(100dvh - 32px))',
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
                  Hi! Ask me how ACME pays people, by country, role or department. I look the numbers up in
                  the salary database.
                </Bubble>
                {messages.length === 0 && (
                  <Stack gap={6} align="flex-start">
                    {EXAMPLES.map((example) => (
                      <Button
                        key={example}
                        variant="light"
                        size="xs"
                        radius="xl"
                        h="auto"
                        py={6}
                        fw={500}
                        styles={{ label: { whiteSpace: 'normal', textAlign: 'left' } }}
                        onClick={() => send(example)}
                      >
                        {example}
                      </Button>
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
                  const { answer, intent } = m.result
                  return (
                    <Bubble key={m.id} from="assistant">
                      <AnswerText answer={answer} />
                      <Group gap={4} mt={8}>
                        <IntentBadge variant="light">{METRIC_LABELS[intent.metric] ?? intent.metric}</IntentBadge>
                        {intent.country && <IntentBadge>Country: {intent.country}</IntentBadge>}
                        {intent.job_title && <IntentBadge>Job title: {intent.job_title}</IntentBadge>}
                        {intent.department && <IntentBadge>Department: {intent.department}</IntentBadge>}
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

function AnswerText({ answer }: { answer: string }) {
  const parts = toAnswerParts(answer)
  if ('text' in parts) return <>{parts.text}</>
  return (
    <>
      {parts.title}
      <List size="sm" spacing={2} mt={4}>
        {parts.items.map((item) => (
          <List.Item key={item}>{item}</List.Item>
        ))}
      </List>
    </>
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

function Bubble({ from, children }: { from: keyof typeof BUBBLE_STYLES; children: ReactNode }) {
  const s = BUBBLE_STYLES[from]
  return (
    <Box
      bg={s.bg}
      c={s.c}
      px="sm"
      py={8}
      maw="85%"
      style={{ alignSelf: s.align, borderRadius: 16, [s.corner]: 4, fontSize: 'var(--mantine-font-size-sm)', lineHeight: 1.45 }}
    >
      {children}
    </Box>
  )
}
