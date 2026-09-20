from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..dependencies import AuthenticatedUser, get_cloud_session, get_current_user
from .schemas import CloudProjectsResponse
from .services import (CloudProjectLimitError, CloudProjectService,
                       LimitsUnavailableError)


router = APIRouter(prefix='/api/v1/cloud/projects', tags=['cloud projects'])


def _response(state) -> CloudProjectsResponse:
    return CloudProjectsResponse(
        cloud_project_ids=state.project_ids,
        cloud_project_count=state.count,
        max_cloud_projects=state.max_cloud_projects,
    )


def _limits_unavailable() -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={
        'code': 'limits_unavailable', 'message': 'Limits are temporarily unavailable.',
    })


async def _reject_request_body(request: Request) -> None:
    """C8 never accepts a project payload, plaintext or otherwise."""
    if await request.body():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={
            'code': 'cloud_project_content_not_accepted',
            'message': 'Cloud project content is not accepted by this API.',
        })


@router.get('', response_model=CloudProjectsResponse)
def list_cloud_projects(current: AuthenticatedUser = Depends(get_current_user),
                        session: Session = Depends(get_cloud_session)) -> CloudProjectsResponse:
    try:
        return _response(CloudProjectService().list(session, current.user.id))
    except LimitsUnavailableError:
        raise _limits_unavailable() from None


@router.post('/{project_id}', response_model=CloudProjectsResponse)
async def enable_cloud_project(project_id: str, request: Request,
                               current: AuthenticatedUser = Depends(get_current_user),
                               session: Session = Depends(get_cloud_session)) -> CloudProjectsResponse:
    if not project_id or len(project_id) > 512:
        raise HTTPException(status_code=422, detail={
            'code': 'invalid_project_id', 'message': 'Project ID is invalid.',
        })
    await _reject_request_body(request)
    try:
        return _response(CloudProjectService().enable(session, current.user.id, project_id))
    except CloudProjectLimitError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
            'code': 'cloud_project_limit_reached',
            'message': 'Cloud project limit reached.',
        }) from None
    except LimitsUnavailableError:
        raise _limits_unavailable() from None


@router.delete('/{project_id}', status_code=status.HTTP_204_NO_CONTENT)
def disable_cloud_project(project_id: str, current: AuthenticatedUser = Depends(get_current_user),
                          session: Session = Depends(get_cloud_session)) -> None:
    if not project_id or len(project_id) > 512:
        raise HTTPException(status_code=422, detail={
            'code': 'invalid_project_id', 'message': 'Project ID is invalid.',
        })
    CloudProjectService().disable(session, current.user.id, project_id)
