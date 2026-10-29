import { describe, expect, it } from 'vitest'
import { toAnswerParts } from './answerFormat'

describe('toAnswerParts', () => {
  it('splits list answers into a title and items', () => {
    expect(toAnswerParts('Average salary by department (USD): Engineering 109,860; Product 96,770.')).toEqual({
      lead: null,
      title: 'Average salary by department (USD)',
      items: ['Engineering 109,860', 'Product 96,770'],
    })
  })

  it('keeps the sentence that leads into a list', () => {
    expect(
      toAnswerParts('Engineering has the highest median salary (USD 100,299). Median salary by department (USD): Engineering 100,299; Sales 88,382.'),
    ).toEqual({
      lead: 'Engineering has the highest median salary (USD 100,299).',
      title: 'Median salary by department (USD)',
      items: ['Engineering 100,299', 'Sales 88,382'],
    })
  })

  it('leaves single-fact answers as plain text', () => {
    const answer = 'Data Analyst in Germany: 38 employees, average EUR 65,974 (min EUR 53,000, max EUR 81,500).'
    expect(toAnswerParts(answer)).toEqual({ text: answer })
  })
})
