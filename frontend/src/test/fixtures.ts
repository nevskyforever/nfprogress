import type { Project } from '@/types/api'

export function projectFixture(overrides: Partial<Project> = {}): Project {
  return {
    id: 'f184de493a344752898ea43f2988dddb',
    name: 'Дом у моря',
    goal: 100_000,
    infinite: false,
    total: 25_000,
    progress: 25,
    deadline: '2027-04-30',
    status: 'активен',
    unit: 'symbols',
    created_at: '2026-08-01',
    updated_at: '2026-08-15',
    completed_at: null,
    personal_goal: 1_000,
    today_goal: 26_000,
    streak_enabled: true,
    streak_status: null,
    streak_length: 0,
    max_streak: 0,
    auto_freeze: true,
    progress_entries: [],
    project_notes: [],
    mindmap: null,
    stages: [],
    stages_enabled: false,
    combine_stage_mindmaps: false,
    parent_project_id: null,
    ...overrides,
  }
}
