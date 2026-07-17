import time

from fastapi.testclient import TestClient

from app.main import app


def unique(prefix: str) -> str:
    return f"{prefix}{time.time_ns() % 100000000}"


def register_and_login(client: TestClient, username: str) -> None:
    assert client.post("/api/auth/register", json={"username": username, "password": "password123"}).status_code == 201
    assert client.post("/api/auth/login", json={"username": username, "password": "password123"}).status_code == 200


def test_auth_permissions_and_pagination_validation():
    with TestClient(app) as student:
        register_and_login(student, unique("student"))
        assert student.post("/api/problems", json={}).status_code == 403
        assert student.get("/api/users").status_code == 403
        assert student.get("/api/problems?page=0").status_code == 422
        assert student.get("/api/submissions?page_size=101").status_code == 422
        assert student.get("/api/submissions?status=invalid").status_code == 422
        assert student.post("/api/auth/logout").status_code == 200
        assert student.get("/api/auth/me").status_code == 401


def test_admin_user_management_and_audit_log():
    with TestClient(app) as admin_client:
        assert admin_client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"}).status_code == 200
        student = TestClient(app)
        username = unique("managed")
        register_and_login(student, username)
        users = admin_client.get("/api/users", params={"page_size": 100}).json()["data"]["items"]
        target = next(item for item in users if item["username"] == username)
        updated = admin_client.put(f"/api/users/{target['id']}", json={"role": "teacher", "is_active": False})
        assert updated.status_code == 200
        assert updated.json()["data"]["role"] == "teacher"
        assert student.get("/api/auth/me").status_code == 403
        audits = admin_client.get("/api/audit-logs", params={"target_id": target["id"]}).json()["data"]
        assert audits["total"] >= 1
        assert audits["items"][0]["action"] == "UPDATE_USER_ROLE"


def test_problem_score_validation_and_duplicate_id():
    problem_id = unique("P")
    problem = {
        "id": problem_id, "title": "Validation", "description": "d", "input_description": "i",
        "output_description": "o", "samples": [{"input": "", "output": ""}], "constraints": "",
        "time_limit": 1, "memory_limit": 128, "difficulty": "easy", "tags": [],
        "test_cases": [{"case_id": "c1", "input": "", "output": "", "score": 90, "is_hidden": True}],
    }
    with TestClient(app) as admin_client:
        admin_client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"})
        assert admin_client.post("/api/problems", json=problem).status_code == 422
        problem["test_cases"][0]["score"] = 100
        assert admin_client.post("/api/problems", json=problem).status_code == 201
        assert admin_client.post("/api/problems", json=problem).status_code == 409
