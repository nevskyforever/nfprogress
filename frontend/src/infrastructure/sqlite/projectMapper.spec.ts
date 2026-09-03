import { describe, expect, it } from 'vitest'
import { mapProjects, type SqliteProjectReadModel } from './projectMapper'
import { calculatePureStatistics } from '@/core/statistics/calculations'

const model = (overrides: Partial<SqliteProjectReadModel> = {}): SqliteProjectReadModel => ({
  mirror_status: 'healthy', projects: [], stages: [], progress_entries: [], project_order: [], ...overrides,
})

describe('SQLite project mapper', () => {
  it('reconstructs a project, nested stages, and progress entries', () => {
    const projects = mapProjects(model({
      projects: [{ id: 'p', project_id: null, name: 'Project', goal: 100, infinite: 0,
        unit: 'symbols', status: 'активен', created_at: '2026-01-01', updated_at: null,
        payload_json: JSON.stringify({ total: 40, progress: 40, stages_enabled: true }) }],
      stages: [{ id: 's', project_id: 'p', name: 'Stage', goal: 50, infinite: 0,
        unit: 'symbols', status: 'активен', created_at: null, updated_at: null,
        payload_json: JSON.stringify({ total: 10, progress: 10 }) }],
      progress_entries: [{ id: 'e', project_id: 'p', stage_id: 's', created_at: '2026-01-02T10:00:00',
        added_symbols: 10, added_progress: 10,
        payload_json: JSON.stringify({ added: 10, added_symbols: 10, new_total: 10, new_total_symbols: 10 }) }],
      project_order: ['p'],
    }))
    expect(projects[0]).toMatchObject({ id: 'p', total: 40, stages_enabled: true })
    expect(projects[0]?.stages[0]).toMatchObject({ id: 's', parent_project_id: 'p', total: 10 })
    expect(projects[0]?.stages[0]?.progress_entries[0]).toMatchObject({ id: 'e', added_symbols: 10 })
  })

  it('keeps infinite goals and tolerates malformed optional payload JSON', () => {
    const [project] = mapProjects(model({ projects: [{ id: 'p', project_id: null, name: 'Infinite',
      goal: null, infinite: 1, unit: 'A4', status: 'активен', created_at: null, updated_at: null,
      payload_json: '{not-json' }], project_order: ['p'] }))
    expect(project).toMatchObject({ id: 'p', goal: null, infinite: true, unit: 'A4', stages: [] })
  })

  it.each(['symbols', 'A4', 'author_list', 'ficbook_pages'] as const)('preserves unit %s', (unit) => {
    const [project] = mapProjects(model({ projects: [{ id: 'p', project_id: null, name: 'P', goal: null,
      infinite: 1, unit, status: 'активен', created_at: null, updated_at: null, payload_json: '{}' }], project_order: ['p'] }))
    expect(project?.unit).toBe(unit)
  })

  it('rejects unhealthy mirrors before exposing rows', () => {
    expect(() => mapProjects(model({ mirror_status: 'dirty' }))).toThrow()
  })

  it('rejects incomplete persisted ordering', () => {
    expect(() => mapProjects(model({
      projects: [{ id: 'p', project_id: null, name: 'P', goal: 1, infinite: 0, unit: 'symbols',
        status: 'активен', created_at: null, updated_at: null, payload_json: '{}' }],
      project_order: [],
    }))).toThrow()
  })

  it('feeds mapped progress entries into pure statistics', () => {
    const [project] = mapProjects(model({
      projects: [{ id: 'p', project_id: null, name: 'P', goal: 100, infinite: 0, unit: 'symbols',
        status: 'активен', created_at: '2026-01-01', updated_at: null,
        payload_json: JSON.stringify({ total: 20 }) }],
      progress_entries: [{ id: 'e', project_id: 'p', stage_id: null, created_at: '2026-01-02T10:00:00',
        added_symbols: 20, added_progress: 20,
        payload_json: JSON.stringify({ added_symbols: 20, created_at: '2026-01-02T10:00:00' }) }],
      project_order: ['p'],
    }))
    const result = calculatePureStatistics({
      entityId: project!.id, unit: project!.unit, createdAt: project!.created_at,
      planningDate: '2026-01-02', total: project!.total,
      progressEntries: project!.progress_entries.map((entry) => ({
        addedSymbols: entry.added_symbols, createdAt: entry.created_at,
      })),
    })
    expect(result.metrics).toMatchObject({ entries_count: 1, total: 20, active_days: 1 })
  })
})
