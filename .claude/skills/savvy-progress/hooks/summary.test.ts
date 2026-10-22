import { expect, test } from 'claude-code/testing'

import { summarize } from './summary'

test('summarize picks the most telling field', async () => {
  expect(summarize('Read', { file_path: '/a/b.txt' })).toBe('/a/b.txt')
  expect(summarize('Bash', { command: 'git   status\n-sb' })).toBe('git status -sb')
  expect(summarize('Grep', { pattern: 'TODO' })).toBe('TODO')
  expect(summarize('TaskList', {})).toBe('TaskList')
})
