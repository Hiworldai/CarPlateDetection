from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .database import create_db_and_tables
from .routers.auth import router as auth_router
from .routers.recognitions import router as recognition_router
from .services.files import ensure_storage_dirs
from .services.recognizer import PlateRecognizer


app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site="lax")


@app.on_event("startup")
def startup() -> None:
    ensure_storage_dirs(settings.upload_dir)
    create_db_and_tables()
    recognizer = PlateRecognizer(settings)
    recognizer.load()
    app.state.recognizer = recognizer
    app.state.guest_jobs = {}


app.mount("/media", StaticFiles(directory=settings.upload_dir), name="media")
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(recognition_router, prefix=settings.api_prefix)


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
