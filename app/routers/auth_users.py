from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth import admin, current_user, hash_password, verify_password
from app.database import get_db
from app.models import AuditLog, User
from app.schemas import Credentials, UserUpdate
from app.serializers import user_view
from app.utils import response

router = APIRouter()


@router.post("/auth/register")
async def register(body: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(409, "username already exists")
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user); db.commit()
    return response(user_view(user), "registered", 201)


@router.post("/auth/login")
async def login(body: Credentials, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid username or password")
    if not user.is_active:
        raise HTTPException(403, "user disabled")
    request.session["user_id"] = user.id
    return response(user_view(user), "logged in")


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return response(None, "logged out")


@router.get("/auth/me")
async def me(user: User = Depends(current_user)):
    return response(user_view(user))


@router.get("/users")
async def users(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                _: User = Depends(admin), db: Session = Depends(get_db)):
    items = db.scalars(select(User).offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(User))
    return response({"items": [user_view(x) for x in items], "total": total, "page": page, "page_size": page_size})


@router.get("/users/{user_id}")
async def user_detail(user_id: str, _: User = Depends(admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "user not found")
    return response(user_view(user))


@router.put("/users/{user_id}")
async def update_user(user_id: str, body: UserUpdate, operator: User = Depends(admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "user not found")
    if user.id == operator.id and not body.is_active: raise HTTPException(400, "cannot disable yourself")
    old_role, old_active = user.role, user.is_active
    user.role, user.is_active, user.updated_at = body.role, body.is_active, datetime.now(timezone.utc)
    if old_role != body.role:
        db.add(AuditLog(operator_id=operator.id, action="UPDATE_USER_ROLE", target_type="user", target_id=user.id,
                        detail=f"{old_role} -> {body.role}"))
    if old_active and not body.is_active:
        db.add(AuditLog(operator_id=operator.id, action="DISABLE_USER", target_type="user", target_id=user.id))
    if old_role == body.role and old_active == body.is_active:
        db.add(AuditLog(operator_id=operator.id, action="UPDATE_USER", target_type="user", target_id=user.id,
                        detail="no changes"))
    db.commit()
    return response(user_view(user))
