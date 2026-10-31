import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app import __version__
from app.api.v1.router import api_router  # importing the API registers every model
from app.core.config import settings
from app.db.base import Base
from app.db.seed import seed_demo_data
from app.db.session import SessionLocal, engine, ensure_lightweight_migrations

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("brightloop")

FRONTEND_BUILD = settings.frontend_build_path
FRONTEND_INDEX = FRONTEND_BUILD / "index.html"
FRONTEND_ASSETS = FRONTEND_BUILD / "_app"
SERVE_FRONTEND = (
    settings.serve_frontend and FRONTEND_INDEX.is_file() and FRONTEND_ASSETS.is_dir()
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # SQLite + create_all is all a scaffold needs; switch to Alembic before
    # the first production deploy.
    Base.metadata.create_all(bind=engine)
    ensure_lightweight_migrations()
    if settings.seed_demo_data:
        with SessionLocal() as db:
            if seed_demo_data(db):
                logger.info("Demo data seeded")
    if settings.serve_frontend and not SERVE_FRONTEND:
        logger.warning(
            "Frontend serving is enabled but %s is missing; run `npm run build` "
            "or set SERVE_FRONTEND=false",
            FRONTEND_BUILD,
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Plans, subscriptions and recurring billing in one place. "
        "Roles: admin (full control), staff (day to day), customer (own portal)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Integrity error: %s", exc)
    return JSONResponse(
        status_code=409,
        content={"detail": "The request conflicts with data that already exists"},
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)

if SERVE_FRONTEND:
    app.mount(
        "/_app",
        StaticFiles(directory=str(FRONTEND_ASSETS)),
        name="frontend-assets",
    )


@app.get("/", include_in_schema=False)
def root():
    if SERVE_FRONTEND:
        return FileResponse(FRONTEND_INDEX, headers={"Cache-Control": "no-cache"})
    return {
        "name": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "environment": settings.environment}


@app.get("/robots.txt", include_in_schema=False)
def robots() -> FileResponse:
    path = FRONTEND_BUILD / "robots.txt"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if not SERVE_FRONTEND:
        raise HTTPException(status_code=404, detail="Not found")
    if full_path in {"api", "_app"} or full_path.startswith(("api/", "_app/")):
        raise HTTPException(status_code=404, detail="Not found")

    candidate = (FRONTEND_BUILD / full_path).resolve()
    if candidate.is_file() and candidate.is_relative_to(FRONTEND_BUILD.resolve()):
        return FileResponse(candidate)

    return FileResponse(FRONTEND_INDEX, headers={"Cache-Control": "no-cache"})
