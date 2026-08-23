from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from ..dependencies import Services, get_services
from ..schemas import (
    ArchiveCommand,
    EntityUpdate,
    ProgressCreate,
    ProgressResult,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ReorderStages,
    StageCreate,
    StatisticsResponse,
    TodaySummaryResponse,
)


router = APIRouter(prefix='/projects', tags=['projects'])


@router.get('', response_model=list[ProjectResponse])
def list_projects(
        services: Annotated[Services, Depends(get_services)],
        project_status: str | None = Query(default=None, alias='status'),
        search: str = '',
        sort: Literal['name', 'deadline', 'progress', 'updated'] = 'progress',
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


@router.get('/today', response_model=TodaySummaryResponse)
def today_summary(
        services: Annotated[Services, Depends(get_services)],
):
    return services.projects.today_summary()


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
    return services.projects.create_stage(project_id, payload.model_dump())


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
