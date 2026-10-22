import { expect, test } from 'claude-code/testing'

import { markFor } from './mark'

test('marks edited and read files, and folders holding them', async () => {
  const marks = { '/r/src/a.ts': 'edit', '/r/README.md': 'read' } as const
  expect(markFor(marks, '/r/src/a.ts', false)).toBe('✎')
  expect(markFor(marks, '/r/README.md', false)).toBe('•')
  expect(markFor(marks, '/r/other.txt', false)).toBe(' ')
  expect(markFor(marks, '/r/src', true)).toBe('·')
  expect(markFor(marks, '/r/docs', true)).toBe(' ')
})
