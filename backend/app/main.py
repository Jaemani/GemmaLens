from contextlib import asynccontextmanager
import secrets

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401
from app.api.routes_analysis import router as analysis_router
from app.api.routes_dictionary import router as dictionary_router
from app.api.routes_documents import router as documents_router
from app.api.routes_health import router as health_router
from app.api.routes_models import router as models_router
from app.api.routes_translation import router as translation_router
from app.api.routes_user_profile import router as user_profile_router
from app.api.routes_video import router as video_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import init_db

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PUBLIC_PATHS = {"/health"}


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if not settings.backend_api_key:
        return await call_next(request)
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    raw_header = request.headers.get("x-gemmalens-api-key") or request.headers.get("authorization", "")
    token = raw_header.removeprefix("Bearer ").strip()
    if secrets.compare_digest(token, settings.backend_api_key):
        return await call_next(request)

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Missing or invalid GemmaLens API key."},
    )


app.include_router(health_router)
app.include_router(models_router)
app.include_router(user_profile_router)
app.include_router(documents_router)
app.include_router(analysis_router)
app.include_router(dictionary_router)
app.include_router(video_router)
app.include_router(translation_router)
