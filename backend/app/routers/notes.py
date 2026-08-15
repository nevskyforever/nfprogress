from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from nfprogress.core.errors import NotFoundError

from ..dependencies import Services, get_services
from ..schemas import MindMapPayload, NoteOrder, NotePatch


router = APIRouter(prefix='/projects/{project_id}', tags=['notes', 'mindmaps'])


def _service(services: Services, project_id: str, stage_id: str | None):
    return services.notes_class(
        services.repository,
        project_id,
        stage_id=stage_id,
    )


@router.get('/notes', response_model=dict[str, Any])
def list_notes(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).load_notes()


@router.post('/notes', response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_note(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).create_note()


@router.get('/notes/{note_id}', response_model=dict[str, Any])
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


@router.patch('/notes/{note_id}', response_model=dict[str, Any])
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


@router.put('/notes/order', response_model=dict[str, Any])
def update_note_order(
        project_id: str,
        payload: NoteOrder,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).update_order(payload.note_ids)


@router.get('/mindmap', response_model=dict[str, Any])
def get_mindmap(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).get_mindmap()


@router.put('/mindmap', response_model=dict[str, Any])
def update_mindmap(
        project_id: str,
        payload: MindMapPayload,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return _service(services, project_id, stage_id).update_mindmap(payload.data)
