from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete

from app.api.routes.chatbi import public_router as chatbi_public_router
from app.api.routes.chatbi import router as chatbi_router
from app.config import get_settings
from app.db.models import ConversationContext
from app.db.session import SessionLocal


settings = get_settings()
expose_api_docs = settings.environment == "development"
project_root = Path(__file__).resolve().parents[1]
frontend_dir = project_root / "frontend"
logger = logging.getLogger(__name__)


app = FastAPI(
    title=get_settings().app_name,
    version="0.1.0",
    description="DataPath trusted ChatBI backend.",
    docs_url="/docs" if expose_api_docs else None,
    redoc_url="/redoc" if expose_api_docs else None,
    openapi_url="/openapi.json" if expose_api_docs else None,
)


@app.on_event("startup")
def clear_development_conversation_history() -> None:
    if settings.environment != "development":
        return
    with SessionLocal() as session:
        session.execute(delete(ConversationContext))
        session.commit()


@app.middleware("http")
async def attach_trace_context(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex}"
    request.state.trace_id = request.headers.get("X-Trace-ID") or f"trace_{uuid.uuid4().hex}"
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Trace-ID"] = request.state.trace_id
    if settings.environment == "development" and (
        request.url.path in {"/", "/app"} or request.url.path.startswith("/frontend/")
    ):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


def error_response(request: Request, status_code: int, code: str, message: str, details=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": getattr(request.state, "request_id", ""),
            "trace_id": getattr(request.state, "trace_id", ""),
            "status": "ERROR",
            "code": code,
            "message": message,
            "retryable": status_code >= 500,
            "details": details or {},
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, error: HTTPException):
    detail = error.detail if isinstance(error.detail, dict) else {"message": str(error.detail)}
    return error_response(
        request,
        error.status_code,
        detail.get("code", "HTTP_ERROR"),
        detail.get("message", "请求失败。"),
        {key: value for key, value in detail.items() if key not in {"code", "message"}},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, error: RequestValidationError):
    return error_response(
        request,
        422,
        "REQUEST_VALIDATION_FAILED",
        "请求结构不合法。",
        {"errors": error.errors()},
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, error: Exception):
    logger.exception(
        "Unhandled request failure request_id=%s trace_id=%s",
        getattr(request.state, "request_id", ""),
        getattr(request.state, "trace_id", ""),
        exc_info=error,
    )
    return error_response(
        request,
        500,
        "INTERNAL_ERROR",
        "查询执行失败，系统未返回数据，请稍后重试。",
    )


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
@app.get("/app", include_in_schema=False)
def frontend_entry() -> FileResponse:
    index_path = frontend_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"code": "FRONTEND_NOT_FOUND", "message": "Frontend entry file was not found."},
        )
    return FileResponse(index_path, media_type="text/html; charset=utf-8")


@app.get("/portfolio/dify-chatbi-workflow.dsl.yml", tags=["Portfolio"])
def dify_chatbi_workflow_dsl() -> FileResponse:
    dsl_path = (
        project_root
        / "document"
        / "development"
        / "technical"
        / "dify-chatbi-workflow.zh-CN.dsl.yml"
    )
    if not dsl_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"code": "DSL_FILE_NOT_FOUND", "message": "Dify workflow DSL file was not found."},
        )
    return FileResponse(
        dsl_path,
        media_type="application/x-yaml; charset=utf-8",
        filename="dify-chatbi-workflow.zh-CN.dsl.yml",
    )


if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

app.include_router(chatbi_public_router)
app.include_router(chatbi_router)
