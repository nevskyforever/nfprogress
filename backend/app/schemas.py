from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


UnitCode = Literal['symbols', 'A4', 'author_list', 'ficbook_pages']
ThemeCode = Literal['system', 'light', 'dark']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class StageCreate(StrictModel):
    name: str
    goal: float | None = None
    infinite: bool = False
    total: float = 0
    deadline: date | None = None
    personal_goal: float = 0
    streak_enabled: bool = False
    auto_freeze: bool = True


class ProjectCreate(StageCreate):
    unit: UnitCode = 'symbols'
    stages: list[StageCreate] = Field(default_factory=list)
    combine_stage_mindmaps: bool = False


class EntityUpdate(StrictModel):
    name: str | None = None
    goal: float | None = None
    infinite: bool | None = None
    total: float | None = None
    unit: UnitCode | None = None
    deadline: date | None = None
    personal_goal: float | None = None
    streak_enabled: bool | None = None
    auto_freeze: bool | None = None
    recalculate_plan: bool = False


class ProjectUpdate(EntityUpdate):
    stages_enabled: bool | None = None
    combine_stage_mindmaps: bool | None = None


class ProgressCreate(StrictModel):
    new_total: float
    stage_id: str | None = None


class ReorderStages(StrictModel):
    stage_ids: list[str]


class ProgressEntryResponse(BaseModel):
    id: str
    new_total: float
    new_total_symbols: float
    added: float
    added_symbols: float
    added_progress: float
    created_at: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    goal: float | None
    infinite: bool
    total: float
    progress: float
    deadline: str | None
    status: str
    unit: UnitCode
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    personal_goal: float = 0
    streak_enabled: bool = False
    streak_status: str | None = None
    streak_length: int = 0
    max_streak: int = 0
    auto_freeze: bool = True
    progress_entries: list[ProgressEntryResponse] = Field(default_factory=list)
    project_notes: list[dict[str, Any]] = Field(default_factory=list)
    mindmap: dict[str, Any] | None = None
    stages: list['ProjectResponse'] = Field(default_factory=list)
    stages_enabled: bool = False
    combine_stage_mindmaps: bool = False
    parent_project_id: str | None = None


class ProgressResult(BaseModel):
    project: ProjectResponse
    entry: ProgressEntryResponse
    added_symbols: float
    game: dict[str, Any] | None = None
    warning: str | None = None


class StatisticsResponse(BaseModel):
    entity_id: str
    unit: UnitCode
    metrics: dict[str, Any]
    timeline: list[dict[str, Any]]


class ArchiveCommand(StrictModel):
    archived: bool


class SettingsPatch(StrictModel):
    values: dict[str, Any]


class NotePatch(StrictModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    checklist: list[dict[str, Any]] | None = None
    color: str | None = None
    pinned: bool | None = None
    archived: bool | None = None


class NoteOrder(StrictModel):
    note_ids: list[str]


class MindMapPayload(StrictModel):
    data: dict[str, Any]


class GameCommandResponse(BaseModel):
    ok: bool = True
    message: str | None = None
    messages: list[str] = Field(default_factory=list)
    result: dict[str, Any] | None = None
    state: dict[str, Any]


class WritingSessionStart(StrictModel):
    duration_minutes: Literal[15, 25, 45, 60]
    target_symbols: int = Field(gt=0)
    intention: str
    mode: Literal['flow', 'sprint', 'deep', 'editing'] = 'flow'


class DailyChallengeSelect(StrictModel):
    option_id: str


class WeeklyChallengeStart(StrictModel):
    challenge_id: str


class CreativeEventResolve(StrictModel):
    choice: Literal['safe', 'risk']


class SpecializationSelect(StrictModel):
    specialization_id: str


class InventoryCommand(StrictModel):
    category: str
    item_id: str
    count: int = Field(default=1, ge=1, le=1000)


class StreakFreezeApply(StrictModel):
    target: Literal['global', 'project']
    project_id: str | None = None


class SkillIncrease(StrictModel):
    points: int = Field(default=1, ge=1, le=1000)


class CountCommand(StrictModel):
    count: int = Field(default=1, ge=1, le=1000)


class CustomAwardCreate(StrictModel):
    name: str = Field(min_length=1, max_length=300)
    price: float = Field(gt=0)


class CustomAwardUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    price: float | None = Field(default=None, gt=0)


class BankProductPreview(StrictModel):
    product_type: Literal['credit', 'deposit']
    amount: float = Field(gt=0)
    days: int = Field(gt=0, le=3650)
    allow_interest_withdrawal: bool = False


class BankCreditOpen(StrictModel):
    amount: float = Field(gt=0)
    days: int = Field(gt=0, le=3650)


class BankDepositOpen(BankCreditOpen):
    allow_interest_withdrawal: bool = False


class MoneyCommand(StrictModel):
    amount: float = Field(gt=0)


class BankEventsCommand(StrictModel):
    auto_pay: bool = True


class BankDepositWithdraw(StrictModel):
    allow_early: bool = False


class SyncConfigure(StrictModel):
    type: Literal['word', 'scrivener']
    path: str
    stage_id: str | None = None
    item_id: str | None = None


class SyncStageQuery(StrictModel):
    stage_id: str | None = None


class WordCountResponse(BaseModel):
    symbols: int


class WordImportResponse(BaseModel):
    changed: bool
    symbols: int
    project: ProjectResponse
    progress: ProgressResult | None = None
