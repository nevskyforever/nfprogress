from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from starlette.concurrency import run_in_threadpool

from nfprogress.core.errors import NotFoundError

from ..content_schemas import (
    MindMapResponse,
    MindMapUpdateResponse,
    XMindImportResponse,
    NoteOrderResponse,
    NotesListResponse,
    ProjectNoteResponse,
)
from ..dependencies import Services, get_services
from ..schemas import MindMapPayload, NoteOrder, NotePatch
from nfprogress.core.services.xmind_import import MAX_ARCHIVE_SIZE, import_xmind


router = APIRouter(prefix='/projects/{project_id}', tags=['notes', 'mindmaps'])


def _service(services: Services, project_id: str, stage_id: str | None):
    return services.notes_class(
        services.repository,
        project_id,
        stage_id=stage_id,
    )


@router.get('/notes', response_model=NotesListResponse)
def list_notes(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).load_notes()


@router.post(
    '/notes',
    response_model=ProjectNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).create_note()


@router.get('/notes/{note_id}', response_model=ProjectNoteResponse)
def get_note(
        project_id: str,
        note_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    note = _service(services, project_id, stage_id).get_note(note_id)
    if note is None:
        raise NotFoundError('Заметка не найдена.')
    return note


@router.patch('/notes/{note_id}', response_model=ProjectNoteResponse)
def update_note(
        project_id: str,
        note_id: str,
        payload: NotePatch,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).update_note(
        note_id, payload.model_dump(exclude_unset=True),
    )


@router.delete('/notes/{note_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
        project_id: str,
        note_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    _service(services, project_id, stage_id).delete_note(note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put('/notes/order', response_model=NoteOrderResponse)
def update_note_order(
        project_id: str,
        payload: NoteOrder,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).update_order(payload.note_ids)


@router.get('/mindmap', response_model=MindMapResponse)
def get_mindmap(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).get_mindmap()


@router.put('/mindmap', response_model=MindMapUpdateResponse)
def update_mindmap(
        project_id: str,
        payload: MindMapPayload,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).update_mindmap(payload.data)


@router.post('/mindmap/import/xmind', response_model=XMindImportResponse)
async def import_xmind_file(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        file: UploadFile = File(...),
        stage_id: str | None = None,
):
    del project_id, services, stage_id
    content = await file.read(MAX_ARCHIVE_SIZE + 1)
    return {'sheets': await run_in_threadpool(
        import_xmind, content, file.filename or 'map.xmind',
    )}
