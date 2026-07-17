from fastapi.testclient import TestClient

from app.main import app


def test_demo_problems_are_seeded_and_listed_first():
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"})
        items = client.get("/api/problems", params={"page_size": 100}).json()["data"]["items"]
        ids = [item["id"] for item in items]
        assert ids[:3] == ["DEMO_A_PLUS_B", "DEMO_MAX_OF_THREE", "DEMO_SUM_1_TO_N"]
        detail = client.get("/api/problems/DEMO_A_PLUS_B").json()["data"]
        assert detail["title"] == "A+B 问题"
        assert "给定两个整数" in detail["description"]
        assert sum(case["score"] for case in detail["test_cases"]) == 100
