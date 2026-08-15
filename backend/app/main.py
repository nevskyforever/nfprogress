from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import engine
from nfprogress.core.errors import DomainError
from nfprogress.core.repositories.storage import PickleRepository
from nfprogress.core.services.content import ContentService
from nfprogress.core.services.game import GameService
from nfprogress.core.services.integrations import DocumentIntegrationService
from nfprogress.core.services.notes import ProjectNotesService
from nfprogress.core.services.projects import ProjectService
from nfprogress.core.services.settings import SettingsService

from .config import RuntimeConfig
from .dependencies import Services, require_session
from .routers import content, game, integrations, notes, projects


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    runtime_config = config or RuntimeConfig.from_env()
    data_dir = runtime_config.data_dir
    if data_dir is None:
        data_dir = (
            engine.get_test_data_dir() if engine.dev_mode
            else engine.get_app_data_dir()
        )
    repository = PickleRepository(data_dir)
    game_service = GameService(repository)
    project_service = ProjectService(repository, game_service=game_service)
    services = Services(
        repository=repository,
        projects=project_service,
        notes_class=ProjectNotesService,
        game=game_service,
        settings=SettingsService(repository, platform=runtime_config.platform),
        content=ContentService(),
        integrations=DocumentIntegrationService(
            repository,
            project_service,
            allow_local_files=runtime_config.allow_local_files,
        ),
    )

    app = FastAPI(
        title='nfprogress API',
        version=engine.version,
        description='Shared API for nfprogress Web, Tauri, and Capacitor clients.',
    )
    app.state.runtime_config = runtime_config
    app.state.services = services
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime_config.allowed_origins),
        allow_credentials=False,
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        allow_headers=['Content-Type', 'X-NFProgress-Token'],
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, error: DomainError):
        return JSONResponse(
            status_code=error.status_code,
            content={'detail': {'code': error.code, 'message': error.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
            _request: Request, error: RequestValidationError,
    ):
        fields = [
            {
                'field': '.'.join(str(part) for part in item['loc']),
                'message': item['msg'],
                'type': item['type'],
            }
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                'detail': {
                    'code': 'invalid_request',
                    'message': 'Запрос содержит неверные данные.',
                    'fields': fields,
                },
            },
        )

    @app.get('/health', tags=['system'])
    def health():
        return {'status': 'ok', 'version': engine.version}

    api_dependencies = [Depends(require_session)]
    app.include_router(projects.router, prefix='/api', dependencies=api_dependencies)
    app.include_router(notes.router, prefix='/api', dependencies=api_dependencies)
    app.include_router(game.router, prefix='/api', dependencies=api_dependencies)
    app.include_router(content.router, prefix='/api', dependencies=api_dependencies)
    app.include_router(integrations.router, prefix='/api', dependencies=api_dependencies)
    return app


app = create_app()
