from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth import current_user, teacher
from app.database import get_db
from app.models import Problem, TestCase, User
from app.schemas import ProblemIn
from app.serializers import problem_view
from app.utils import response

router = APIRouter()


def apply_problem(problem: Problem, body: ProblemIn) -> None:
    problem.title = body.title
    problem.description = body.description
    problem.input_description = body.input_description
    problem.output_description = body.output_description
    problem.samples_json = json.dumps([x.model_dump() for x in body.samples], ensure_ascii=False)
    problem.constraints = body.constraints
    problem.time_limit = body.time_limit
    problem.memory_limit = body.memory_limit
    problem.difficulty = body.difficulty
    problem.tags_json = json.dumps(body.tags, ensure_ascii=False)
    problem.test_cases = [TestCase(case_id=x.case_id, input_data=x.input, expected_output=x.output,
                                   score=x.score, is_hidden=x.is_hidden) for x in body.test_cases]


@router.get("/problems")
async def list_problems(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                        user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Problem).order_by(Problem.id)
                       .offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(Problem))
    summaries = [{k: problem_view(x)[k] for k in ("id", "title", "difficulty", "tags", "time_limit", "memory_limit")} for x in items]
    return response({"items": summaries, "total": total, "page": page, "page_size": page_size})


@router.get("/problems/{problem_id}")
async def get_problem(problem_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(Problem, problem_id)
    if not item:
        raise HTTPException(404, "problem not found")
    return response(problem_view(item, user.role in {"teacher", "admin"}))


@router.post("/problems")
async def create_problem(body: ProblemIn, _: User = Depends(teacher), db: Session = Depends(get_db)):
    if db.get(Problem, body.id):
        raise HTTPException(409, "problem id already exists")
    item = Problem(id=body.id, title="", description="", input_description="", output_description="",
                   samples_json="[]", time_limit=1, memory_limit=128, difficulty="easy")
    apply_problem(item, body)
    db.add(item)
    db.commit()
    return response(problem_view(item, True), "problem created", 201)


@router.put("/problems/{problem_id}")
async def update_problem(problem_id: str, body: ProblemIn, _: User = Depends(teacher), db: Session = Depends(get_db)):
    if body.id != problem_id:
        raise HTTPException(400, "problem id cannot be changed")
    item = db.get(Problem, problem_id)
    if not item:
        raise HTTPException(404, "problem not found")
    apply_problem(item, body)
    db.commit()
    return response(problem_view(item, True))


@router.delete("/problems/{problem_id}")
async def delete_problem(problem_id: str, _: User = Depends(teacher), db: Session = Depends(get_db)):
    item = db.get(Problem, problem_id)
    if not item:
        raise HTTPException(404, "problem not found")
    db.delete(item)
    db.commit()
    return response(None, "problem deleted")
