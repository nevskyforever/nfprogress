from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ..dependencies import Services, get_services
from ..schemas import (
    CreativeEventResolve,
    DailyChallengeSelect,
    GameCommandResponse,
    InventoryCommand,
    SkillIncrease,
    SpecializationSelect,
    WeeklyChallengeStart,
    WritingSessionStart,
)


router = APIRouter(prefix='/game', tags=['game'])


@router.get('/state', response_model=dict[str, Any])
def state(services: Annotated[Services, Depends(get_services)]):
    return services.game.get_state()


@router.get('/catalog', response_model=dict[str, Any])
def catalog(services: Annotated[Services, Depends(get_services)]):
    return services.game.get_shop_catalog()


@router.post('/writing-sessions/start', response_model=GameCommandResponse)
def start_writing_session(
        payload: WritingSessionStart,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.start_writing_session(
        payload.duration_minutes,
        payload.target_symbols,
        payload.intention,
        mode_key=payload.mode,
    )


@router.post('/writing-sessions/finish', response_model=GameCommandResponse)
def finish_writing_session(services: Annotated[Services, Depends(get_services)]):
    return services.game.finish_writing_session()


@router.post('/writing-sessions/cancel', response_model=GameCommandResponse)
def cancel_writing_session(services: Annotated[Services, Depends(get_services)]):
    return services.game.cancel_writing_session()


@router.post('/daily-challenge/select', response_model=GameCommandResponse)
def select_daily_challenge(
        payload: DailyChallengeSelect,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.select_daily_challenge(payload.option_id)


@router.post('/weekly-challenge/start', response_model=GameCommandResponse)
def start_weekly_challenge(
        payload: WeeklyChallengeStart,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.start_weekly_challenge(payload.challenge_id)


@router.post(
    '/inspiration-abilities/{ability_id}/activate',
    response_model=GameCommandResponse,
)
def activate_inspiration_ability(
        ability_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.activate_inspiration_ability(ability_id)


@router.post('/creative-events/resolve', response_model=GameCommandResponse)
def resolve_creative_event(
        payload: CreativeEventResolve,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.resolve_creative_event(payload.choice)


@router.post('/specialization/select', response_model=GameCommandResponse)
def select_specialization(
        payload: SpecializationSelect,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.select_specialization(payload.specialization_id)


@router.post('/specialization/ability/activate', response_model=GameCommandResponse)
def activate_specialization_ability(
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.activate_specialization_ability()


@router.post('/skills/{skill_id}/increase', response_model=GameCommandResponse)
def increase_skill(
        skill_id: str,
        payload: SkillIncrease,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.increase_skill(skill_id, payload.points)


@router.post('/quests/{quest_id}/start', response_model=GameCommandResponse)
def start_quest(
        quest_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.start_quest(quest_id)


@router.post('/quests/{quest_id}/abandon', response_model=GameCommandResponse)
def abandon_quest(
        quest_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.abandon_quest(quest_id)


@router.post('/inventory/buy', response_model=GameCommandResponse)
def buy_item(
        payload: InventoryCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.buy_item(payload.category, payload.item_id, payload.count)


@router.post('/inventory/sell', response_model=GameCommandResponse)
def sell_item(
        payload: InventoryCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.sell_item(payload.category, payload.item_id, payload.count)


@router.post('/inventory/use', response_model=GameCommandResponse)
def use_item(
        payload: InventoryCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.use_item(payload.category, payload.item_id, payload.count)
