import { describe, expect, it } from 'vitest'
import { toAnswerParts } from './answerFormat'

describe('toAnswerParts', () => {
  it('splits list answers into a title and items', () => {
    expect(toAnswerParts('Average salary by department (USD): Engineering 109,860; Product 96,770.')).toEqual({
      title: 'Average salary by department (USD)',
      items: ['Engineering 109,860', 'Product 96,770'],
    })
  })

  it('leaves single-fact answers as plain text', () => {
    const answer = 'Data Analyst in Germany: 38 employees, average EUR 65,974 (min EUR 53,000, max EUR 81,500).'
    expect(toAnswerParts(answer)).toEqual({ text: answer })
  })
})
