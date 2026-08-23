from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from ..dependencies import Services, get_services
from ..schemas import (
    ScrivenerItemResponse,
    ProjectSyncsResponse,
    SyncBatchResponse,
    SyncConfigure,
    SyncDetachAllResponse,
    SyncRunResponse,
    SyncSummaryResponse,
    WordCountResponse,
    WordImportResponse,
)


router = APIRouter(tags=['integrations'])


@router.get('/projects/{project_id}/sync', response_model=SyncSummaryResponse)
def get_sync(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return services.integrations.get_sync(project_id, stage_id=stage_id)


@router.get('/projects/{project_id}/sync/all', response_model=ProjectSyncsResponse)
def get_project_syncs(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.integrations.get_project_syncs(project_id)


@router.put('/projects/{project_id}/sync', response_model=SyncSummaryResponse)
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


@router.delete('/projects/{project_id}/sync', response_model=SyncSummaryResponse)
def remove_sync(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return services.integrations.remove_sync(project_id, stage_id=stage_id)


@router.delete(
    '/projects/{project_id}/sync/all',
    response_model=SyncDetachAllResponse,
)
def remove_all_syncs(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.integrations.remove_all_syncs(project_id)


@router.post('/projects/{project_id}/sync/run-all', response_model=SyncBatchResponse)
def run_project_syncs(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.integrations.run_project_syncs(project_id)


@router.post('/projects/{project_id}/sync/run', response_model=SyncRunResponse)
def run_sync(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return services.integrations.run_sync(project_id, stage_id=stage_id)


@router.post('/integrations/sync/run-all', response_model=SyncBatchResponse)
def run_all_sync(services: Annotated[Services, Depends(get_services)]):
    return services.integrations.sync_all_configured()


@router.get(
    '/integrations/scrivener/items',
    response_model=list[ScrivenerItemResponse],
)
def scrivener_items(
        path: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.integrations.inspect_scrivener(path)


@router.post('/integrations/word/count', response_model=WordCountResponse)
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


@router.post(
    '/projects/{project_id}/imports/word',
    response_model=WordImportResponse,
)
async def apply_word_upload(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        file: UploadFile = File(...),
        stage_id: str | None = None,
):
    content = await file.read(100 * 1024 * 1024 + 1)
    return await run_in_threadpool(
        services.integrations.apply_uploaded_docx,
        project_id,
        content,
        file.filename or 'document.docx',
        stage_id=stage_id,
    )
