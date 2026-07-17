from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select, update

from app.auth import hash_password
from app.config import ADMIN_PASSWORD, ADMIN_USERNAME, BASE_DIR, SESSION_SECRET, ensure_directories
from app.database import Base, SessionLocal, engine
from app.models import Submission, User
from app.routers import admin, auth_users, problems, submissions


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories(); Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.username == ADMIN_USERNAME)):
            db.add(User(username=ADMIN_USERNAME, password_hash=hash_password(ADMIN_PASSWORD), role="admin")); db.commit()
        now = datetime.now(timezone.utc)
        db.execute(update(Submission).where(Submission.status.in_(["pending", "running"])).values(
            status="failed", result="SE", finished_at=now
        ))
        db.commit()
    yield


app = FastAPI(title="Mini OJ", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")
for router in (auth_users.router, problems.router, submissions.router, admin.router):
    app.include_router(router, prefix="/api")


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code, "message": str(exc.detail), "data": None})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=jsonable_encoder(
        {"code": 422, "message": "validation error", "data": exc.errors()},
        custom_encoder={ValueError: str},
    ))


@app.exception_handler(Exception)
async def internal_error(_: Request, __: Exception):
    return JSONResponse(status_code=500, content={"code": 500, "message": "internal server error", "data": None})


@app.get("/", include_in_schema=False)
async def frontend():
    return FileResponse(BASE_DIR / "frontend" / "index.html")
