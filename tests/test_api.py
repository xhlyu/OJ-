import time

from fastapi.testclient import TestClient

from app.main import app


PROBLEM = {
    "id": "P1001", "title": "A+B", "description": "sum", "input_description": "two ints",
    "output_description": "sum", "samples": [{"input": "1 2\n", "output": "3\n"}],
    "constraints": "", "time_limit": 1, "memory_limit": 128, "difficulty": "easy", "tags": ["basic"],
    "test_cases": [{"case_id": "public", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
                   {"case_id": "hidden", "input": "5 7\n", "output": "12\n", "score": 50, "is_hidden": True}],
}


def test_full_flow():
    with TestClient(app) as admin:
        assert admin.post("/api/auth/login", json={"username": "admin", "password": "admin12345"}).status_code == 200
        created = admin.post("/api/problems", json=PROBLEM)
        assert created.status_code in {201, 409}
        student = TestClient(app)
        username = f"student{time.time_ns() % 1000000}"
        assert student.post("/api/auth/register", json={"username": username, "password": "password123"}).status_code == 201
        assert student.post("/api/auth/login", json={"username": username, "password": "password123"}).status_code == 200
        detail = student.get("/api/problems/P1001").json()["data"]
        assert "test_cases" not in detail
        submitted = student.post("/api/submissions", json={"problem_id": "P1001", "language": "python",
                                                           "source_code": "a,b=map(int,input().split());print(a+b)"})
        assert submitted.status_code == 202
        sid = submitted.json()["data"]["submission_id"]
        for _ in range(50):
            item = student.get(f"/api/submissions/{sid}").json()["data"]
            if item["status"] in {"finished", "failed"}: break
            time.sleep(0.05)
        assert item["status"] == "finished" and item["result"] == "AC" and item["score"] == 100
        logs = student.get(f"/api/submissions/{sid}/logs").json()["data"]["cases"]
        hidden = next(x for x in logs if x["case_id"] == "hidden")
        assert "expected_output" not in hidden and "input_data" not in hidden and "stdout" not in hidden
