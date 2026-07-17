import time

from fastapi.testclient import TestClient

from app.main import app


def login_admin(client: TestClient) -> None:
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"}).status_code == 200


def problem_payload(problem_id: str, title: str = "Lifecycle") -> dict:
    return {
        "id": problem_id, "title": title, "description": "description", "input_description": "input",
        "output_description": "output", "samples": [{"input": "1\n", "output": "1\n"}],
        "constraints": "", "time_limit": 1, "memory_limit": 128, "difficulty": "easy", "tags": ["test"],
        "test_cases": [{"case_id": "public", "input": "1\n", "output": "1\n", "score": 100, "is_hidden": False}],
    }


def test_problem_update_delete_preserves_submission():
    problem_id = f"LIFE{time.time_ns() % 10000000}"
    with TestClient(app) as client:
        login_admin(client)
        payload = problem_payload(problem_id)
        assert client.post("/api/problems", json=payload).status_code == 201
        payload["title"] = "Updated title"
        payload["difficulty"] = "medium"
        updated = client.put(f"/api/problems/{problem_id}", json=payload)
        assert updated.status_code == 200
        assert updated.json()["data"]["title"] == "Updated title"
        changed_id = dict(payload, id=problem_id + "X")
        assert client.put(f"/api/problems/{problem_id}", json=changed_id).status_code == 400
        submitted = client.post("/api/submissions", json={
            "problem_id": problem_id, "language": "python", "source_code": "print(input())"
        })
        submission_id = submitted.json()["data"]["submission_id"]
        assert client.delete(f"/api/problems/{problem_id}").status_code == 200
        assert client.get(f"/api/problems/{problem_id}").status_code == 404
        history = client.get(f"/api/submissions/{submission_id}")
        assert history.status_code == 200
        assert history.json()["data"]["problem_id"] == problem_id
        assert client.get(f"/api/submissions/{submission_id}/logs").status_code == 200


def test_student_never_receives_test_cases():
    problem_id = f"HIDE{time.time_ns() % 10000000}"
    with TestClient(app) as admin_client:
        login_admin(admin_client)
        assert admin_client.post("/api/problems", json=problem_payload(problem_id)).status_code == 201
    student = TestClient(app)
    username = f"viewer{time.time_ns() % 10000000}"
    student.post("/api/auth/register", json={"username": username, "password": "password123"})
    student.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert "test_cases" not in student.get(f"/api/problems/{problem_id}").json()["data"]
