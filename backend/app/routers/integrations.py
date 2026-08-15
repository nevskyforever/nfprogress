from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from ..dependencies import Services, get_services
from ..schemas import SyncConfigure


router = APIRouter(tags=['integrations'])


@router.get('/projects/{project_id}/sync', response_model=dict[str, Any])
def get_sync(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return services.integrations.get_sync(project_id, stage_id=stage_id)


@router.put('/projects/{project_id}/sync', response_model=dict[str, Any])
def configure_sync(
        project_id: str,
        payload: SyncConfigure,
        services: Annotated[Services, Depends(get_services)],
):
    return services.integrations.configure_sync(
        project_id,
        sync_type=payload.type,
        path=payload.path,
        stage_id=payload.stage_id,
        item_id=payload.item_id,
    )


@router.delete('/projects/{project_id}/sync', response_model=dict[str, Any])
def remove_sync(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return services.integrations.remove_sync(project_id, stage_id=stage_id)


@router.post('/projects/{project_id}/sync/run', response_model=dict[str, Any])
def run_sync(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return services.integrations.run_sync(project_id, stage_id=stage_id)


@router.get('/integrations/scrivener/items', response_model=list[dict[str, str]])
def scrivener_items(
        path: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.integrations.inspect_scrivener(path)


@router.post('/integrations/word/count', response_model=dict[str, int])
async def count_word_upload(
        services: Annotated[Services, Depends(get_services)],
        file: UploadFile = File(...),
):
    content = await file.read(100 * 1024 * 1024 + 1)
    symbols = await run_in_threadpool(
        services.integrations.count_uploaded_docx,
        content,
        file.filename or 'document.docx',
    )
    return {'symbols': symbols}
