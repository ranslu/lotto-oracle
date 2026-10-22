import type { Touched } from '../types'

/** The marker shown next to an entry: ✎ edited, • read, · folder holding touched files. */
export function markFor(marks: Touched, path: string, isDir: boolean): string {
  if (!isDir) return marks[path] === 'edit' ? '✎' : marks[path] === 'read' ? '•' : ' '
  return Object.keys(marks).some(k => k.startsWith(`${path}/`)) ? '·' : ' '
}
