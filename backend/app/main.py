from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.api.v1.router import api_router
from backend.app.db.base import Base
from backend.app.db.session import engine
import backend.app.db.models.entities

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all storage and data directories exist
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    settings.data_root.mkdir(parents=True, exist_ok=True)
    settings.logs_root.mkdir(parents=True, exist_ok=True)
    settings.temp_path.mkdir(parents=True, exist_ok=True)
    settings.cache_path.mkdir(parents=True, exist_ok=True)
    settings.thumbnails_path.mkdir(parents=True, exist_ok=True)
    settings.frames_path.mkdir(parents=True, exist_ok=True)
    settings.transcripts_path.mkdir(parents=True, exist_ok=True)
    settings.metadata_path.mkdir(parents=True, exist_ok=True)
    settings.reports_path.mkdir(parents=True, exist_ok=True)
    settings.saved_videos_path.mkdir(parents=True, exist_ok=True)

    # Initialize tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()

import logging
import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "HTTP_ERROR"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 429:
        code = "UPSTREAM_RATE_LIMIT"
    elif exc.status_code == 400:
        code = "BAD_REQUEST"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 500:
        code = "INTERNAL_SERVER_ERROR"

    msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": msg,
                "status_code": exc.status_code,
                "retryable": exc.status_code in (429, 503, 504),
                "details": exc.detail if isinstance(exc.detail, dict) else None
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}\n{traceback.format_exc()}")
    
    code = getattr(exc, "code", "INTERNAL_SERVER_ERROR")
    retryable = getattr(exc, "retryable", False)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": code,
                "message": str(exc) or "An unexpected internal server error occurred.",
                "status_code": 500,
                "retryable": retryable,
                "details": {
                    "path": request.url.path,
                    "method": request.method,
                    "exception_type": exc.__class__.__name__
                }
            }
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
