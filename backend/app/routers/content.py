from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..content_schemas import (
    HelpSectionResponse,
    LanguageOptionResponse,
    SettingsResponse,
)
from ..dependencies import Services, get_services
from ..schemas import AgreementAcceptance, AgreementResponse, SettingsPatch


router = APIRouter(tags=['content'])


@router.get('/content/languages', response_model=list[LanguageOptionResponse])
def languages(services: Annotated[Services, Depends(get_services)]):
    return services.content.languages()


@router.get('/content/locales/{language}', response_model=dict[str, str])
def locale(language: str, services: Annotated[Services, Depends(get_services)]):
    return services.content.locale(language)


@router.get('/content/help', response_model=list[HelpSectionResponse])
def help_content(
        services: Annotated[Services, Depends(get_services)],
        language: str = 'ru',
):
    return services.content.help(language)


@router.get('/content/agreement', response_model=AgreementResponse)
def user_agreement(
        services: Annotated[Services, Depends(get_services)],
        language: str = 'ru',
):
    return services.content.agreement(language)


@router.get('/settings', response_model=SettingsResponse)
def get_settings(services: Annotated[Services, Depends(get_services)]):
    return services.settings.get()


@router.patch('/settings', response_model=SettingsResponse)
def update_settings(
        payload: SettingsPatch,
        services: Annotated[Services, Depends(get_services)],
):
    return services.settings.update(payload.values)


@router.post('/settings/user-agreement/accept', response_model=SettingsResponse)
def accept_user_agreement(
        payload: AgreementAcceptance,
        services: Annotated[Services, Depends(get_services)],
):
    return services.settings.accept_user_agreement(payload.agreement_id)
