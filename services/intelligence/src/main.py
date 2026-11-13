import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from src.application.research_use_cases import ResearchRequestError
from src.domain.exceptions import DomainError, NotFoundError
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.persistence.database import create_database
from src.presentation.api.research import router as research_router
from src.presentation.api.routers import router
from src.presentation.api.schemas import ErrorResponse
from src.presentation.api.source_intelligence import router as source_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine, factory = create_database(config.database_url)
        app.state.session_factory = factory
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="Universe Atlas",
        version="0.1.0",
        lifespan=lifespan,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    app.state.settings = config
    app.include_router(source_router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.exception_handler(NotFoundError)
    async def missing(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"code": "not_found", "message": str(exc)})

    @app.exception_handler(DomainError)
    async def invalid(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"code": "invalid_graph", "message": str(exc)})

    @app.exception_handler(ResearchRequestError)
    async def invalid_research(_: Request, exc: ResearchRequestError) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"code": "invalid_research_request", "message": str(exc)}
        )

    @app.exception_handler(RequestValidationError)
    async def validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "invalid_request", "message": "Invalid request parameters"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def unavailable(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Database operation failed", exc_info=exc)
        return JSONResponse(
            status_code=503,
            content={"code": "database_unavailable", "message": "Local database is unavailable"},
        )

    app.add_exception_handler(ConnectionError, unavailable)
    app.add_exception_handler(TimeoutError, unavailable)
    app.include_router(router)
    app.include_router(research_router)
    return app


app = create_app()
