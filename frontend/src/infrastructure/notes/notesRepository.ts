import { currentPlatform } from '@/platform/runtime'
import type { NotesRepository } from '@/core/repositories/notes'
import { ApiNotesRepository } from '@/infrastructure/api/notesRepository'
import { SQLiteNotesRepository } from '@/infrastructure/sqlite/notesRepository'

const apiRepository = new ApiNotesRepository()
const sqliteRepository = new SQLiteNotesRepository()

export function getNotesRepository(): NotesRepository {
  return currentPlatform() === 'tauri' ? sqliteRepository : apiRepository
}
