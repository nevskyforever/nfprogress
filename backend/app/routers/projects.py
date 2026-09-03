from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from ..dependencies import Services, get_services
from ..schemas import (
    ArchiveCommand,
    EntityUpdate,
    GlobalStreakSummaryResponse,
    ProgressCreate,
    ProgressResult,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectMetadataPatch,
    ProjectFolderCreate,
    ProjectFolderResponse,
    ProjectFolderUpdate,
    ReorderProjects,
    ReorderStages,
    StageCreate,
    StatisticsResponse,
    TodaySummaryResponse,
)


router = APIRouter(prefix='/projects', tags=['projects'])


def _migrate_first_stage_document(
        services: Services, project_id: str, was_single_project: bool,
) -> None:
    if not was_single_project:
        return
    project = services.projects.get_project(project_id)
    stages = project.get('stages', [])
    first_stage = stages[0] if isinstance(stages, list) and stages else None
    stage_id = first_stage.get('id') if isinstance(first_stage, dict) else None
    if isinstance(stage_id, str) and stage_id:
        services.documents.move_project_document_to_stage(project_id, stage_id)


@router.get('', response_model=list[ProjectResponse])
def list_projects(
        services: Annotated[Services, Depends(get_services)],
        project_status: str | None = Query(default=None, alias='status'),
        search: str = '',
        sort: Literal['manual', 'name', 'deadline', 'progress', 'updated'] = 'manual',
):
    return services.projects.list_projects(
        status=project_status, search=search, sort=sort,
    )


@router.post('', response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
        payload: ProjectCreate,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.create_project(payload.model_dump())


@router.get('/folders', response_model=list[ProjectFolderResponse])
def list_project_folders(
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.list_folders()


@router.post('/folders', response_model=ProjectFolderResponse, status_code=status.HTTP_201_CREATED)
def create_project_folder(
        payload: ProjectFolderCreate,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.create_folder(payload.name)


@router.patch('/folders/{folder_id}', response_model=ProjectFolderResponse)
def update_project_folder(
        folder_id: str,
        payload: ProjectFolderUpdate,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.update_folder(folder_id, payload.name)


@router.delete('/folders/{folder_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_project_folder(
        folder_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    services.projects.delete_folder(folder_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put('/order', response_model=list[ProjectResponse])
def reorder_projects(
        payload: ReorderProjects,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.reorder_projects(payload.project_ids)


@router.get('/today', response_model=TodaySummaryResponse)
def today_summary(
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.today_summary()


@router.get('/streaks/global', response_model=GlobalStreakSummaryResponse)
def global_streak_summary(
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.global_streak_summary()


@router.get('/{project_id}', response_model=ProjectResponse)
def get_project(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.get_project(project_id)


@router.patch('/{project_id}', response_model=ProjectResponse)
def update_project(
        project_id: str,
        payload: ProjectUpdate,
        services: Annotated[Services, Depends(get_services)],
):
    current = services.projects.get_project(project_id)
    was_single_project = not current.get('stages')
    result = services.projects.update_project(
        project_id, payload.model_dump(exclude_unset=True),
    )
    _migrate_first_stage_document(services, project_id, was_single_project and payload.stages_enabled is True)
    return result


@router.patch('/{project_id}/metadata', response_model=ProjectResponse)
def update_project_metadata(
        project_id: str,
        payload: ProjectMetadataPatch,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.update_project(
        project_id, payload.model_dump(exclude_unset=True),
    )


@router.delete('/{project_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    services.projects.delete_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/{project_id}/archive', response_model=ProjectResponse)
def archive_project(
        project_id: str,
        payload: ArchiveCommand,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.set_project_archived(project_id, payload.archived)


@router.post('/{project_id}/complete', response_model=ProjectResponse)
def complete_project(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.complete_project(project_id)


@router.post(
    '/{project_id}/stages', response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stage(
        project_id: str,
        payload: StageCreate,
        services: Annotated[Services, Depends(get_services)],
):
    current = services.projects.get_project(project_id)
    was_single_project = not current.get('stages')
    result = services.projects.create_stage(project_id, payload.model_dump())
    _migrate_first_stage_document(services, project_id, was_single_project)
    return result


@router.patch('/{project_id}/stages/{stage_id}', response_model=ProjectResponse)
def update_stage(
        project_id: str,
        stage_id: str,
        payload: EntityUpdate,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.update_stage(
        project_id, stage_id, payload.model_dump(exclude_unset=True),
    )


@router.delete(
    '/{project_id}/stages/{stage_id}', status_code=status.HTTP_204_NO_CONTENT,
)
def delete_stage(
        project_id: str,
        stage_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    services.projects.delete_stage(project_id, stage_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put('/{project_id}/stages/order', response_model=ProjectResponse)
def reorder_stages(
        project_id: str,
        payload: ReorderStages,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.reorder_stages(project_id, payload.stage_ids)


@router.post('/{project_id}/stages/{stage_id}/complete', response_model=ProjectResponse)
def complete_stage(
        project_id: str,
        stage_id: str,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.complete_stage(project_id, stage_id)


@router.post('/{project_id}/progress', response_model=ProgressResult)
def record_progress(
        project_id: str,
        payload: ProgressCreate,
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.record_progress(
        project_id, stage_id=payload.stage_id, new_total=payload.new_total,
    )


@router.delete('/{project_id}/progress/{entry_id}', response_model=ProjectResponse)
def delete_progress(
        project_id: str,
        entry_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return services.projects.delete_progress(
        project_id, entry_id, stage_id=stage_id,
    )


@router.get('/{project_id}/statistics', response_model=StatisticsResponse)
def statistics(
        project_id: str,
        services: Annotated[Services, Depends(get_services)],
        stage_id: str | None = None,
):
    return services.projects.statistics(project_id, stage_id=stage_id)
