from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class GameResponseModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class JsonExtensionResponse(GameResponseModel):
    """A stable envelope whose canonical legacy metadata may grow over time."""

    model_config = ConfigDict(extra='allow')
    __pydantic_extra__: dict[str, JsonValue] = Field(init=False)


class PendingBonusesResponse(GameResponseModel):
    writing: float
    session: float
    challenge: float
    manuscript: float


class GameProfileResponse(GameResponseModel):
    level: int
    experience: float
    next_level_experience: int | None
    coins: float
    inflation: float
    health: float
    max_health: float
    inspiration: float
    max_inspiration: int
    writing_session_streak: int
    session_streak_shields: int
    session_grade_boosts: int
    pending_bonuses: PendingBonusesResponse


class GameSkillResponse(GameResponseModel):
    key: str
    name: str
    points: int
    target: str
    bonus: float


class GameCoefficientResponse(GameResponseModel):
    key: str
    name: str
    description: str
    value: float
    base_value: float


class GameSkillsResponse(GameResponseModel):
    available_points: int
    points_per_level: int
    items: list[GameSkillResponse]
    coefficients: list[GameCoefficientResponse]


class GameBuffResponse(GameResponseModel):
    name: str
    description: str
    type: str
    target: str
    value: float
    stacks: int
    duration_minutes: int | None
    started_at: str | None
    expires_at: str | None
    remaining_seconds: int | None
    source: str | None
    stackable: bool


class GameBuffsResponse(GameResponseModel):
    server_time: str
    positive: list[GameBuffResponse]
    negative: list[GameBuffResponse]


class GameItemResponse(JsonExtensionResponse):
    # Registered and forward-compatible legacy inventory rows share these
    # fields. Registry-specific price, level and buff metadata stays as typed
    # JSON extras so unknown save-compatible items are never filtered out.
    id: str
    key: str
    category: str
    name: str
    description: str | None
    count: int
    sellable: bool
    usable: bool
    buy: bool = False


class InventoryGameItemResponse(GameItemResponse):
    known: bool


class GameItemCategoryResponse(GameResponseModel):
    key: str
    name: str
    items: list[GameItemResponse]


class InventoryItemCategoryResponse(GameResponseModel):
    key: str
    name: str
    items: list[InventoryGameItemResponse]


class GameInventoryResponse(GameResponseModel):
    categories: list[InventoryItemCategoryResponse]


class StreakSourceResponse(GameResponseModel):
    id: str
    name: str
    is_stage: bool
    streak_length: int


class ProjectStreakFreezeResponse(GameResponseModel):
    project_id: str
    name: str
    source_count: int
    max_streak: int
    sources: list[StreakSourceResponse]


class StreakFreezesResponse(GameResponseModel):
    date: str
    inventory_count: int
    global_available: bool
    projects: list[ProjectStreakFreezeResponse]


class QuestRewardResponse(GameResponseModel):
    coins: float
    experience: float
    items: JsonValue
    buffs: list[GameBuffResponse]


class GameQuestResponse(GameResponseModel):
    id: str
    name: str
    description: str
    status: str
    required_level: int
    started_at: str | None
    finished_at: str | None
    reward: QuestRewardResponse


class GameQuestsResponse(GameResponseModel):
    items: list[GameQuestResponse]
    # Status keys are canonical legacy values and can be extended without an
    # API envelope change; each projected quest remains fully typed.
    by_status: dict[str, list[GameQuestResponse]]


class RewardSummaryResponse(GameResponseModel):
    coins: float
    experience: float
    inspiration: int


class DailyChallengeOptionResponse(GameResponseModel):
    option_id: str
    date: str
    type: str
    name: str
    description: str
    difficulty: str
    difficulty_name: str
    target: int
    progress: int
    completed: bool
    reward: RewardSummaryResponse


class DailyChallengeResponse(GameResponseModel):
    change_cost: int
    current: DailyChallengeOptionResponse | None
    options: list[DailyChallengeOptionResponse]
    history: list[JsonValue]


class WeeklyChallengeResponse(GameResponseModel):
    key: str
    name: str
    description: str
    target: int
    reward: RewardSummaryResponse


class ActiveWeeklyChallengeResponse(WeeklyChallengeResponse):
    week_start: str
    progress: int
    writing_days: list[str]
    completed: bool


class WeeklyChallengesResponse(GameResponseModel):
    current: ActiveWeeklyChallengeResponse | None
    catalog: list[WeeklyChallengeResponse]


class ActiveWritingSessionResponse(GameResponseModel):
    started_at: str | None
    ends_at: str | None
    duration_minutes: int
    target_symbols: int
    progress: int
    intention: str
    mode: str
    remaining_seconds: int


class WritingSessionModeResponse(GameResponseModel):
    key: str
    name: str
    description: str
    reward_bonus: float


class WritingSessionGradeResponse(GameResponseModel):
    key: str
    name: str
    target_ratio: float
    reward_multiplier: float


class WritingSessionResponse(GameResponseModel):
    server_time: str
    active: ActiveWritingSessionResponse | None
    streak: int
    # Historical entries intentionally remain extensible for old saves and
    # future result metadata, but are still guaranteed to be JSON-safe.
    history: list[JsonValue]
    modes: list[WritingSessionModeResponse]
    grades: list[WritingSessionGradeResponse]
    allowed_durations_minutes: list[int]


class InspirationAbilityResponse(GameResponseModel):
    key: str
    name: str
    description: str
    cost: int
    bonus: float
    active: bool


class CreativeEventResponse(GameResponseModel):
    key: str
    name: str
    description: str
    safe_description: str
    risk_description: str
    safe: JsonValue
    risk: JsonValue


class InspirationResponse(GameResponseModel):
    abilities: list[InspirationAbilityResponse]
    creative_event: CreativeEventResponse | None
    creative_event_history: list[JsonValue]


class SpecializationAbilityResponse(GameResponseModel):
    name: str
    description: str
    cooldown_hours: int
    remaining_seconds: int
    pending: bool


class SpecializationResponse(GameResponseModel):
    key: str
    name: str
    description: str
    selected: bool
    mastery_experience: int
    mastery_rank: int
    passive_bonus: float
    ability: SpecializationAbilityResponse


class SpecializationsResponse(GameResponseModel):
    selected: str | None
    unlocks_at_level: int
    change_cooldown_days: int
    change_days_remaining: int
    mastery_thresholds: list[int]
    items: list[SpecializationResponse]


class ManuscriptJourneyResponse(GameResponseModel):
    owner_key: str
    owner_name: str | None
    received_milestones: list[int]


class ManuscriptMilestoneResponse(GameResponseModel):
    progress: int
    name: str
    coins: int
    exp: int
    inspiration: int


class CabinetRelicResponse(GameResponseModel):
    key: str
    unlocked: bool
    name: str | None
    description: str | None
    condition: str
    progress: int
    required: int
    effect_type: str | None
    bonus: float | None
    effect_description: str | None


class CabinetSetResponse(GameResponseModel):
    key: str
    name: str
    description: str
    relics: list[str]
    unlocked: bool
    effect_type: str
    bonus: float


class CabinetResponse(GameResponseModel):
    relics: list[CabinetRelicResponse]
    sets: list[CabinetSetResponse]


class ManuscriptsResponse(GameResponseModel):
    journeys: list[ManuscriptJourneyResponse]
    milestones: list[ManuscriptMilestoneResponse]
    cabinet: CabinetResponse


class BankCreditResponse(GameResponseModel):
    principal: float
    interest_rate: float
    interest: float
    total: float
    remaining: float
    daily_payment: float
    status: str
    opened_at: str | None
    return_date: str | None
    paid_amount: float
    overdue_days: int


class BankDepositResponse(GameResponseModel):
    principal: float
    interest_rate: float
    interest: float
    total: float
    available_interest: float
    allow_interest_withdrawal: bool
    status: str
    opened_at: str | None
    return_date: str | None


class BankResponse(GameResponseModel):
    credit_score: int | None
    credit_limit: float
    max_credit_days: int
    credit_rate: float
    deposit_rate: float
    estimated_daily_income: JsonValue
    can_open_credit: bool
    can_open_deposit: bool
    credit: BankCreditResponse | None
    deposit: BankDepositResponse | None
    credit_history_count: int
    deposit_history_count: int
    overdue_days_total: int


class CustomAwardResponse(GameResponseModel):
    id: str
    name: str
    description: str
    price: float
    sell_price: float
    count: int
    available_in_shop: bool
    sellable: bool
    usable: bool
    can_buy: bool


class CustomAwardsResponse(GameResponseModel):
    items: list[CustomAwardResponse]


class ShopCatalogResponse(GameResponseModel):
    categories: list[GameItemCategoryResponse]
    custom_awards: CustomAwardsResponse


class GameCatalogResponse(ShopCatalogResponse):
    enabled: bool


class GameNotificationResponse(GameResponseModel):
    id: str
    text: str
    tag: str | None
    created_at: str | None
    status: Literal['new', 'read']


class GameNotificationsResponse(GameResponseModel):
    unread: list[GameNotificationResponse]
    read: list[GameNotificationResponse]
    unread_count: int


class GameStateResponse(GameResponseModel):
    enabled: bool
    server_time: str
    profile: GameProfileResponse
    skills: GameSkillsResponse
    buffs: GameBuffsResponse
    inventory: GameInventoryResponse
    notifications: GameNotificationsResponse
    streak_freezes: StreakFreezesResponse
    quests: GameQuestsResponse
    daily_challenge: DailyChallengeResponse
    weekly_challenge: WeeklyChallengesResponse
    writing_session: WritingSessionResponse
    inspiration: InspirationResponse
    specializations: SpecializationsResponse
    manuscripts: ManuscriptsResponse
    bank: BankResponse
    custom_awards: CustomAwardsResponse
    shop: ShopCatalogResponse


class GameCommandResponse(GameResponseModel):
    ok: bool = True
    message: str | None = None
    messages: list[str] = Field(default_factory=list)
    result: dict[str, JsonValue] | None = None
    state: GameStateResponse


class DeveloperModeResponse(GameResponseModel):
    state: GameStateResponse
    test_date_enabled: bool
    test_datetime: str | None


__all__ = [
    'GameCatalogResponse',
    'GameCommandResponse',
    'DeveloperModeResponse',
    'GameNotificationsResponse',
    'GameStateResponse',
]
