from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..schemas import AuthLoginIn, AuthUserOut

router = APIRouter()


@router.get("/auth/me", response_model=AuthUserOut)
def get_me(request: Request) -> AuthUserOut:
    username = request.session.get("username")
    if username:
        return AuthUserOut(authenticated=True, username=username, storage_mode="server")
    return AuthUserOut(authenticated=False, storage_mode="local")


@router.post("/auth/login", response_model=AuthUserOut)
def login(payload: AuthLoginIn, request: Request) -> AuthUserOut:
    if payload.username != settings.admin_username or payload.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="账号或密码错误")

    request.session["username"] = payload.username
    return AuthUserOut(authenticated=True, username=payload.username, storage_mode="server")


@router.post("/auth/logout", response_model=AuthUserOut)
def logout(request: Request) -> AuthUserOut:
    request.session.clear()
    return AuthUserOut(authenticated=False, storage_mode="local")
