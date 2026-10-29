export type AnswerParts = { lead: string | null; title: string; items: string[] } | { text: string }

/**
 * The backend renders ranked answers as "[Lead sentence.] Title: a; b; c." — show the list as a
 * list (or drop it when a table already shows the same rows). Anything else stays plain text.
 */
export function toAnswerParts(answer: string): AnswerParts {
  const match = /^(?:(.*\.) )?([^:.;]+): ([^:]+;[^:]+)\.$/.exec(answer)
  if (!match) return { text: answer }
  return { lead: match[1] ?? null, title: match[2], items: match[3].split('; ') }
}
