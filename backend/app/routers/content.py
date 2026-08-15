from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ..dependencies import Services, get_services
from ..schemas import SettingsPatch


router = APIRouter(tags=['content'])


@router.get('/content/languages')
def languages(services: Annotated[Services, Depends(get_services)]):
    return services.content.languages()


@router.get('/content/locales/{language}', response_model=dict[str, str])
def locale(language: str, services: Annotated[Services, Depends(get_services)]):
    return services.content.locale(language)


@router.get('/content/help', response_model=list[dict[str, Any]])
def help_content(
        services: Annotated[Services, Depends(get_services)],
        language: str = 'ru',
):
    return services.content.help(language)


@router.get('/settings', response_model=dict[str, Any])
def get_settings(services: Annotated[Services, Depends(get_services)]):
    return services.settings.get()


@router.patch('/settings', response_model=dict[str, Any])
def update_settings(
        payload: SettingsPatch,
        services: Annotated[Services, Depends(get_services)],
):
    return services.settings.update(payload.values)
