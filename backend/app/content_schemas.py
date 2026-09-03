from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


SupportedLanguage = Literal['ru', 'en', 'es', 'de', 'fr', 'pt_BR']
BackendPlatform = Literal['desktop', 'web', 'ios', 'android']
EditableSettingKey = Literal[
    'background_synch',
    'frontend_project_filter',
    'frontend_project_sort',
    'frontend_stage_sort',
    'frontend_motion',
    'frontend_theme',
    'game_mode',
    'global_streak',
    'inf_project',
    'inventory_filter',
    'language',
    'notification_display_time',
    'project_filter',
    'project_sort',
    'show_written_today_in_all_projects',
    'start_day_time',
]
NoteSourceType = Literal['project', 'mindmap']
NoteOwnerType = Literal['project', 'stage']
NoteContentFormat = Literal['html', 'plain']


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class LanguageOptionResponse(ResponseModel):
    code: SupportedLanguage
    display_name: str


class HelpSectionResponse(ResponseModel):
    key: str
    title: str
    content: str
    children: list[HelpSectionResponse]


class PlatformCapabilitiesResponse(ResponseModel):
    local_file_sync: bool
    background_file_sync: bool
    native_updates: bool
    remote_api: bool


class SettingsResponse(ResponseModel):
    # Legacy settings may contain UI state owned by either frontend during the
    # transition. Values are still constrained to the JSON boundary while the
    # stable response envelope remains explicit in OpenAPI.
    values: dict[str, JsonValue]
    version: str | None = None
    platform: BackendPlatform
    capabilities: PlatformCapabilitiesResponse
    editable_keys: list[EditableSettingKey]


class NoteChecklistItemResponse(ResponseModel):
    id: str
    text: str
    checked: bool


class ProjectNoteResponse(ResponseModel):
    id: str
    project_id: str | None = None
    stage_id: str | None = None
    title: str
    display_title: str
    content: str
    content_format: NoteContentFormat
    checklist: list[NoteChecklistItemResponse]
    color: str
    pinned: bool
    archived: bool
    sort_order: int
    tags: list[str]
    system_tags: list[str]
    source_type: NoteSourceType
    source_map_id: str | None
    source_node_id: str | None
    created_at: str
    updated_at: str
    revision: int
    owner_type: NoteOwnerType
    owner_id: str
    owner_order: int
    stage_name: str | None
    read_only: bool
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class NotesContextStageResponse(ResponseModel):
    id: str
    name: str


class NotesViewContextResponse(ResponseModel):
    hasStages: bool
    stages: list[NotesContextStageResponse]


class NotesListResponse(ResponseModel):
    notes: list[ProjectNoteResponse]
    read_only: bool
    context: NotesViewContextResponse


class NoteOrderResponse(ResponseModel):
    changed: bool
    notes: list[ProjectNoteResponse]


class MindMapResponse(ResponseModel):
    project_id: str
    stage_id: str | None
    name: str
    # Mind Elixir owns an extensible JSON document. The API types its stable
    # envelope without pretending that arbitrary plugin node fields are fixed.
    data: dict[str, JsonValue] | None
    combined: bool
    read_only: bool
    has_empty_completed_stage_map: bool


class MindMapUpdateResponse(MindMapResponse):
    notes: list[ProjectNoteResponse]


class XMindSheetResponse(ResponseModel):
    title: str
    data: dict[str, JsonValue]


class XMindImportResponse(ResponseModel):
    sheets: list[XMindSheetResponse]


__all__ = [
    'HelpSectionResponse',
    'LanguageOptionResponse',
    'MindMapResponse',
    'MindMapUpdateResponse',
    'NoteOrderResponse',
    'NotesListResponse',
    'PlatformCapabilitiesResponse',
    'ProjectNoteResponse',
    'SettingsResponse',
    'XMindImportResponse',
    'XMindSheetResponse',
]
