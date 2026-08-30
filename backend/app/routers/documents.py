from typing import Annotated, Any
from fastapi import APIRouter, Depends
from ..dependencies import Services, get_services

router = APIRouter(prefix='/documents', tags=['documents'])

def scope(project_id: str, stage_id: str | None) -> dict[str, str | None]:
    return {'project_id': project_id, 'stage_id': stage_id}

@router.get('')
def list_documents(services: Annotated[Services, Depends(get_services)]):
    return services.documents.list_existing()

@router.get('/{project_id}')
def get_document(project_id: str, services: Annotated[Services, Depends(get_services)], stage_id: str | None = None):
    return services.documents.get(**scope(project_id, stage_id))

@router.put('/{project_id}')
def save_document(project_id: str, payload: dict[str, Any], services: Annotated[Services, Depends(get_services)], stage_id: str | None = None):
    return services.documents.save(project_id, payload['content'], stage_id)

@router.put('/{project_id}/link')
def link_document(project_id: str, payload: dict[str, str], services: Annotated[Services, Depends(get_services)], stage_id: str | None = None):
    return services.documents.link(project_id, payload['path'], stage_id)

@router.put('/{project_id}/docx')
def write_docx(project_id: str, payload: dict[str, str], services: Annotated[Services, Depends(get_services)], stage_id: str | None = None):
    return services.documents.write_docx(project_id, payload['content_base64'], stage_id)

@router.get('/{project_id}/external')
def external_docx(project_id: str, services: Annotated[Services, Depends(get_services)], stage_id: str | None = None):
    return services.documents.read_external_docx(project_id, stage_id)

@router.put('/{project_id}/accept-word')
def accept_word(project_id: str, payload: dict[str, Any], services: Annotated[Services, Depends(get_services)], stage_id: str | None = None):
    return services.documents.accept_word(project_id, payload['content'], payload['source_hash'], stage_id)

@router.post('/{project_id}/progress')
def record_text_progress(project_id: str, services: Annotated[Services, Depends(get_services)], stage_id: str | None = None):
    return services.documents.record_text_progress(project_id, stage_id)
