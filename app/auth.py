import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(401, "not authenticated")
    user = db.get(User, user_id)
    if not user:
        request.session.clear()
        raise HTTPException(401, "user not found")
    if not user.is_active:
        raise HTTPException(403, "user disabled")
    return user


async def teacher(user: User = Depends(current_user)) -> User:
    if user.role not in {"teacher", "admin"}:
        raise HTTPException(403, "teacher permission required")
    return user


async def admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "admin permission required")
    return user
