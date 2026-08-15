from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ..dependencies import Services, get_services
from ..schemas import (
    BankCreditOpen,
    BankDepositOpen,
    BankDepositWithdraw,
    BankEventsCommand,
    BankProductPreview,
    CountCommand,
    CreativeEventResolve,
    CustomAwardCreate,
    CustomAwardUpdate,
    DailyChallengeSelect,
    GameCommandResponse,
    InventoryCommand,
    MoneyCommand,
    SkillIncrease,
    SpecializationSelect,
    StreakFreezeApply,
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


@router.post('/streak-freezes/apply', response_model=GameCommandResponse)
def apply_streak_freeze(
        payload: StreakFreezeApply,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.apply_streak_freeze(
        payload.target,
        project_id=payload.project_id,
    )


@router.post('/custom-awards', response_model=GameCommandResponse)
def create_custom_award(
        payload: CustomAwardCreate,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.create_custom_award(payload.name, payload.price)


@router.patch('/custom-awards/{award_id}', response_model=GameCommandResponse)
def update_custom_award(
        award_id: str,
        payload: CustomAwardUpdate,
        services: Annotated[Services, Depends(get_services)],
):
    values = payload.model_dump(exclude_unset=True)
    return services.game.update_custom_award(award_id, **values)


@router.delete('/custom-awards/{award_id}', response_model=GameCommandResponse)
def delete_custom_award(
        award_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.delete_custom_award(award_id)


@router.post('/custom-awards/{award_id}/buy', response_model=GameCommandResponse)
def buy_custom_award(
        award_id: str,
        payload: CountCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.buy_custom_award(award_id, payload.count)


@router.post('/custom-awards/{award_id}/sell', response_model=GameCommandResponse)
def sell_custom_award(
        award_id: str,
        payload: CountCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.sell_custom_award(award_id, payload.count)


@router.post('/custom-awards/{award_id}/use', response_model=GameCommandResponse)
def use_custom_award(
        award_id: str,
        payload: CountCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.use_custom_award(award_id, payload.count)


@router.post('/bank/preview', response_model=GameCommandResponse)
def preview_bank_product(
        payload: BankProductPreview,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.preview_bank_product(
        payload.product_type,
        payload.amount,
        payload.days,
        allow_interest_withdrawal=payload.allow_interest_withdrawal,
    )


@router.post('/bank/credit', response_model=GameCommandResponse)
def open_bank_credit(
        payload: BankCreditOpen,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.open_bank_credit(payload.amount, payload.days)


@router.post('/bank/deposit', response_model=GameCommandResponse)
def open_bank_deposit(
        payload: BankDepositOpen,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.open_bank_deposit(
        payload.amount,
        payload.days,
        allow_interest_withdrawal=payload.allow_interest_withdrawal,
    )


@router.post('/bank/process', response_model=GameCommandResponse)
def process_bank_events(
        payload: BankEventsCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.process_bank_events(auto_pay=payload.auto_pay)


@router.post('/bank/credit/payment', response_model=GameCommandResponse)
def make_bank_loan_payment(
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.make_bank_loan_payment()


@router.post('/bank/credit/partial-repayment', response_model=GameCommandResponse)
def partially_repay_bank_credit(
        payload: MoneyCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.partially_repay_bank_credit(payload.amount)


@router.post('/bank/credit/repay', response_model=GameCommandResponse)
def repay_bank_credit(
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.repay_bank_credit()


@router.post('/bank/deposit/top-up', response_model=GameCommandResponse)
def top_up_bank_deposit(
        payload: MoneyCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.top_up_bank_deposit(payload.amount)


@router.post('/bank/deposit/withdraw', response_model=GameCommandResponse)
def withdraw_bank_deposit(
        payload: BankDepositWithdraw,
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.withdraw_bank_deposit(allow_early=payload.allow_early)


@router.post('/bank/deposit/interest/withdraw', response_model=GameCommandResponse)
def withdraw_bank_deposit_interest(
        services: Annotated[Services, Depends(get_services)],
):
    return services.game.withdraw_bank_deposit_interest()
