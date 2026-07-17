import asyncio
from datetime import datetime, timezone

from app.database import SessionLocal
from app.judge.runner import run_judge
from app.models import JudgeLog, Problem, Submission
from app.utils import truncate_text


async def evaluate_submission(submission_id: str) -> None:
    db = SessionLocal()
    try:
        submission = db.get(Submission, submission_id)
        problem = db.get(Problem, submission.problem_id) if submission else None
        if not submission or not problem:
            return
        submission.status = "running"
        submission.started_at = datetime.now(timezone.utc)
        db.commit()
        try:
            result, score, total_time, cases = await run_judge(
                submission.source_code, problem.test_cases, problem.time_limit
            )
            for case in cases:
                db.add(JudgeLog(submission_id=submission.id, case_id=case.case_id, result=case.result,
                                score=case.score, time_used=case.time_used, exit_code=case.exit_code,
                                input_data=truncate_text(case.input_data), stdout=truncate_text(case.stdout),
                                stderr=truncate_text(case.stderr), expected_output=truncate_text(case.expected_output),
                                message=truncate_text(case.message), is_hidden=case.is_hidden))
            submission.result = result
            submission.score = score
            submission.total_time = total_time
            submission.status = "failed" if result == "SE" else "finished"
        except Exception as exc:
            submission.status = "failed"
            submission.result = "SE"
            db.add(JudgeLog(submission_id=submission.id, case_id="system", result="SE", score=0,
                            message=truncate_text(str(exc)), is_hidden=True))
        submission.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def schedule_submission(submission_id: str) -> None:
    asyncio.create_task(evaluate_submission(submission_id))
