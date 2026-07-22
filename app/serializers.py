from __future__ import annotations

import json

from app.models import JudgeLog, Problem, Submission, User
from app.utils import iso, sanitize_error, student_error_view


def user_view(user: User) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active,
            "created_at": iso(user.created_at), "updated_at": iso(user.updated_at)}


def problem_view(problem: Problem, full: bool = False) -> dict:
    data = {"id": problem.id, "title": problem.title, "description": problem.description,
            "input_description": problem.input_description, "output_description": problem.output_description,
            "samples": json.loads(problem.samples_json), "constraints": problem.constraints,
            "time_limit": problem.time_limit, "memory_limit": problem.memory_limit,
            "difficulty": problem.difficulty, "tags": json.loads(problem.tags_json),
            "judge_mode": problem.judge_mode}
    if full:
        data["checker_code"] = problem.checker_code
        data["test_cases"] = [{"case_id": c.case_id, "input": c.input_data, "output": c.expected_output,
                               "score": c.score, "is_hidden": c.is_hidden} for c in problem.test_cases]
    return data


def submission_view(item: Submission, include_source: bool = True) -> dict:
    data = {"id": item.id, "user_id": item.user_id, "problem_id": item.problem_id,
            "language": item.language, "status": item.status, "result": item.result, "score": item.score,
            "total_time": item.total_time, "created_at": iso(item.created_at), "started_at": iso(item.started_at),
            "finished_at": iso(item.finished_at)}
    if include_source:
        data["source_code"] = item.source_code
    return data


def log_view(log: JudgeLog, full: bool) -> dict:
    data = {"case_id": log.case_id, "result": log.result, "score": log.score,
            "time_used": log.time_used, "message": sanitize_error(log.message),
            "stderr": sanitize_error(log.stderr) if full else student_error_view(log.stderr),
            "created_at": iso(log.created_at)}
    if full or not log.is_hidden:
        data.update({"stdout": log.stdout, "expected_output": log.expected_output})
    if full:
        data.update({"input_data": log.input_data, "exit_code": log.exit_code,
                     "is_hidden": log.is_hidden, "memory_used": log.memory_used})
    return data
