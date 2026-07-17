from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth import current_user, teacher
from app.config import MAX_SOURCE_SIZE
from app.database import get_db
from app.models import AuditLog, JudgeLog, Problem, Submission, User
from app.schemas import SubmissionIn
from app.serializers import log_view, submission_view
from app.services import evaluate_submission
from app.utils import iso, response

router = APIRouter()


@router.post("/submissions")
async def create_submission(body: SubmissionIn, background_tasks: BackgroundTasks,
                            user: User = Depends(current_user), db: Session = Depends(get_db)):
    if len(body.source_code.encode("utf-8")) > MAX_SOURCE_SIZE: raise HTTPException(422, "source code exceeds 64 KiB")
    if not db.get(Problem, body.problem_id): raise HTTPException(404, "problem not found")
    item = Submission(user_id=user.id, problem_id=body.problem_id, language=body.language, source_code=body.source_code)
    db.add(item); db.commit()
    background_tasks.add_task(evaluate_submission, item.id)
    return response({"submission_id": item.id, "status": "pending"}, "submission accepted", 202)


@router.get("/submissions")
async def list_submissions(page: int = 1, page_size: int = 20, problem_id: str | None = None,
                           user_id: str | None = None, status: str | None = None, result: str | None = None,
                           user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Submission)
    if user.role == "student": query = query.where(Submission.user_id == user.id)
    elif user_id: query = query.where(Submission.user_id == user_id)
    if problem_id: query = query.where(Submission.problem_id == problem_id)
    if status: query = query.where(Submission.status == status)
    if result: query = query.where(Submission.result == result)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Submission.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return response({"items": [submission_view(x, False) for x in items], "total": total, "page": page, "page_size": page_size})


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(Submission, submission_id)
    if not item: raise HTTPException(404, "submission not found")
    if user.role == "student" and item.user_id != user.id: raise HTTPException(403, "not your submission")
    return response(submission_view(item))


@router.post("/submissions/{submission_id}/rejudge")
async def rejudge(submission_id: str, background_tasks: BackgroundTasks,
                  operator: User = Depends(teacher), db: Session = Depends(get_db)):
    item = db.get(Submission, submission_id)
    if not item: raise HTTPException(404, "submission not found")
    if item.status not in {"finished", "failed"}: raise HTTPException(409, "submission is not ready for rejudge")
    item.status="pending"; item.result=None; item.score=0; item.total_time=None; item.started_at=None; item.finished_at=None
    db.execute(delete(JudgeLog).where(JudgeLog.submission_id == item.id))
    db.add(AuditLog(operator_id=operator.id, action="REJUDGE_SUBMISSION", target_type="submission", target_id=item.id))
    db.commit(); background_tasks.add_task(evaluate_submission, item.id)
    return response({"submission_id": item.id, "status": "pending"}, "rejudge accepted", 202)


@router.get("/submissions/{submission_id}/logs")
async def submission_logs(submission_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(Submission, submission_id)
    if not item: raise HTTPException(404, "submission not found")
    if user.role == "student" and item.user_id != user.id: raise HTTPException(403, "not your submission")
    full = user.role in {"teacher", "admin"}
    logs = db.scalars(select(JudgeLog).where(JudgeLog.submission_id == item.id)).all()
    if full:
        db.add(AuditLog(operator_id=user.id, action="VIEW_FULL_JUDGE_LOG", target_type="submission", target_id=item.id)); db.commit()
    return response({"submission": submission_view(item, False), "cases": [log_view(x, full) for x in logs]})


@router.get("/logs")
async def all_logs(page: int = 1, page_size: int = 20, submission_id: str | None = None,
                   _: User = Depends(teacher), db: Session = Depends(get_db)):
    query = select(JudgeLog)
    if submission_id: query = query.where(JudgeLog.submission_id == submission_id)
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return response({"items": [log_view(x, True) | {"submission_id": x.submission_id} for x in items], "page": page, "page_size": page_size})
