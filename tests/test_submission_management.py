import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Submission
from app.services import transition_submission


def wait_finished(client: TestClient, submission_id: str) -> dict:
    for _ in range(100):
        item = client.get(f"/api/submissions/{submission_id}").json()["data"]
        if item["status"] in {"finished", "failed"}:
            return item
        time.sleep(0.05)
    raise AssertionError("submission did not finish")


def login_admin(client: TestClient) -> None:
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"}).status_code == 200


def test_status_transition_guard():
    submission = SimpleNamespace(status="pending")
    transition_submission(submission, "running")
    transition_submission(submission, "finished")
    with pytest.raises(ValueError):
        transition_submission(submission, "running")


def test_rejudge_and_full_log_audit():
    with TestClient(app) as admin_client:
        login_admin(admin_client)
        problem_id = f"REJUDGE{time.time_ns() % 1000000}"
        problem = {
            "id": problem_id, "title": "Rejudge", "description": "d", "input_description": "i",
            "output_description": "o", "samples": [{"input": "", "output": "ok\n"}], "constraints": "",
            "time_limit": 1, "memory_limit": 128, "difficulty": "easy", "tags": [],
            "test_cases": [{"case_id": "hidden", "input": "secret\n", "output": "ok\n", "score": 100, "is_hidden": True}],
        }
        assert admin_client.post("/api/problems", json=problem).status_code == 201
        submitted = admin_client.post("/api/submissions", json={
            "problem_id": problem_id, "language": "python", "source_code": "input(); print('ok')"
        })
        submission_id = submitted.json()["data"]["submission_id"]
        assert wait_finished(admin_client, submission_id)["result"] == "AC"
        full_logs = admin_client.get(f"/api/submissions/{submission_id}/logs").json()["data"]["cases"]
        assert full_logs[0]["input_data"] == "secret\n"
        assert full_logs[0]["expected_output"] == "ok\n"
        rejudge = admin_client.post(f"/api/submissions/{submission_id}/rejudge")
        assert rejudge.status_code == 202
        assert wait_finished(admin_client, submission_id)["result"] == "AC"
        audits = admin_client.get("/api/audit-logs", params={"target_id": submission_id, "page_size": 100}).json()["data"]["items"]
        actions = {item["action"] for item in audits}
        assert {"VIEW_FULL_JUDGE_LOG", "REJUDGE_SUBMISSION"} <= actions


def test_rejudge_rejects_running_submission():
    with TestClient(app) as admin_client:
        login_admin(admin_client)
        admin_id = admin_client.get("/api/auth/me").json()["data"]["id"]
        with SessionLocal() as db:
            running = Submission(
                user_id=admin_id, problem_id="DEMO_A_PLUS_B", language="python",
                source_code="print(3)", status="running",
            )
            db.add(running)
            db.commit()
            submission_id = running.id
        response = admin_client.post(f"/api/submissions/{submission_id}/rejudge")
        assert response.status_code == 409
        assert response.json()["message"] == "submission is not ready for rejudge"


def test_submission_view_contains_all_required_assignment_fields():
    with TestClient(app) as client:
        login_admin(client)
        created = client.post("/api/submissions", json={
            "problem_id": "DEMO_A_PLUS_B", "language": "python",
            "source_code": "a, b = map(int, input().split()); print(a + b)",
        })
        assert created.status_code == 202
        submission_id = created.json()["data"]["submission_id"]
        detail = client.get(f"/api/submissions/{submission_id}").json()["data"]
        assert {
            "id", "user_id", "problem_id", "language", "source_code", "status", "result",
            "score", "total_time", "created_at", "started_at", "finished_at",
        } <= detail.keys()
