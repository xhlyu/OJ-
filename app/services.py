from datetime import datetime, timezone

from app.database import SessionLocal
from app.judge.runner import run_judge
from app.models import JudgeLog, Problem, Submission
from app.utils import truncate_text


ALLOWED_TRANSITIONS = {
    "pending": {"running", "failed"},
    "running": {"finished", "failed"},
    "finished": set(),
    "failed": set(),
}


def transition_submission(submission: Submission, target: str) -> None:
    if target not in ALLOWED_TRANSITIONS.get(submission.status, set()):
        raise ValueError(f"invalid submission status transition: {submission.status} -> {target}")
    submission.status = target


async def evaluate_submission(submission_id: str) -> None:
    db = SessionLocal()
    try:
        submission = db.get(Submission, submission_id)
        if not submission:
            return
        problem = db.get(Problem, submission.problem_id)
        if not problem:
            transition_submission(submission, "failed")
            submission.result = "SE"
            submission.finished_at = datetime.now(timezone.utc)
            db.add(JudgeLog(submission_id=submission.id, case_id="system", result="SE", score=0,
                            message="problem configuration is unavailable", is_hidden=True))
            db.commit()
            return
        transition_submission(submission, "running")
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
            transition_submission(submission, "failed" if result == "SE" else "finished")
        except Exception as exc:
            transition_submission(submission, "failed")
            submission.result = "SE"
            db.add(JudgeLog(submission_id=submission.id, case_id="system", result="SE", score=0,
                            message=truncate_text(str(exc)), is_hidden=True))
        submission.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
