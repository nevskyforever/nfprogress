/** Canonical project units shared with the Python project model. */
export type ProgressUnit = 'symbols' | 'A4' | 'author_list' | 'ficbook_pages'

export interface FiniteGoal {
  goal: number | null
  total: number
  infinite: boolean
}
