from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from .database import SessionLocal
from .services.recognizer import PlateRecognizer


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_recognizer(request: Request) -> PlateRecognizer:
    return request.app.state.recognizer


def get_optional_user(request: Request) -> str | None:
    return request.session.get("username")


def require_user(user: str | None = None, request: Request | None = None) -> str:
    resolved_user = user
    if resolved_user is None and request is not None:
        resolved_user = request.session.get("username")
    if not resolved_user:
        raise HTTPException(status_code=401, detail="Please login first")
    return resolved_user
