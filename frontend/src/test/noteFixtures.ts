import type { MindMapResponse, ProjectNote } from '@/types/notes'

export function noteFixture(overrides: Partial<ProjectNote> = {}): ProjectNote {
  return {
    id: 'note-id',
    title: 'Первая встреча',
    display_title: 'Первая встреча',
    content: '<p>Герои встречаются у старого маяка.</p>',
    content_format: 'html',
    checklist: [],
    color: 'teal',
    pinned: false,
    archived: false,
    sort_order: 0,
    tags: ['персонажи'],
    system_tags: [],
    source_type: 'project',
    source_map_id: null,
    source_node_id: null,
    created_at: '2026-08-15T10:00:00+00:00',
    updated_at: '2026-08-15T10:00:00+00:00',
    revision: 0,
    owner_type: 'project',
    owner_id: 'project-id',
    owner_order: 0,
    stage_name: null,
    read_only: false,
    ...overrides,
  }
}

export function mindMapFixture(overrides: Partial<MindMapResponse> = {}): MindMapResponse {
  return {
    project_id: 'project-id',
    stage_id: null,
    name: 'Дом у моря',
    data: {
      nodeData: {
        id: 'root-id',
        topic: 'Дом у моря',
        children: [],
      },
      linkData: {},
    },
    combined: false,
    read_only: false,
    has_empty_completed_stage_map: false,
    ...overrides,
  }
}
