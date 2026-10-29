export type AnswerParts = { title: string; items: string[] } | { text: string }

/**
 * The backend renders ranked answers as "Title: a; b; c." — show those as a list.
 * Anything else (single facts, help text) stays as plain text.
 */
export function toAnswerParts(answer: string): AnswerParts {
  const match = /^([^:]+): (.+;.+)\.$/.exec(answer)
  if (!match) return { text: answer }
  return { title: match[1], items: match[2].split('; ') }
}
