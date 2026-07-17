import time

from fastapi.testclient import TestClient

from app.main import app


def login_admin(client: TestClient) -> None:
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"}).status_code == 200


def test_bcrypt_byte_limit_and_username_whitespace():
    with TestClient(app) as client:
        assert client.post("/api/auth/register", json={"username": " spaced ", "password": "password123"}).status_code == 422
        too_many_bytes = "密" * 25
        response = client.post("/api/auth/register", json={"username": f"bytes{time.time_ns() % 1000000}", "password": too_many_bytes})
        assert response.status_code == 422
        assert response.json()["code"] == 422


def test_log_search_creates_audit_and_returns_timestamp():
    with TestClient(app) as client:
        login_admin(client)
        existing = client.get("/api/submissions", params={"page_size": 100}).json()["data"]["items"]
        if not existing:
            return
        submission_id = existing[0]["id"]
        logs = client.get("/api/logs", params={"submission_id": submission_id, "page_size": 100})
        assert logs.status_code == 200
        items = logs.json()["data"]["items"]
        if not items:
            return
        assert items[0]["created_at"].endswith("Z")
        audits = client.get("/api/audit-logs", params={"action": "VIEW_FULL_JUDGE_LOG", "target_id": submission_id,
                                                       "page_size": 100}).json()["data"]["items"]
        assert any(item["detail"] == "viewed through log search" for item in audits)


def test_password_hash_never_appears_in_user_api():
    with TestClient(app) as client:
        login_admin(client)
        payload = client.get("/api/users", params={"page_size": 100}).text.lower()
        assert "password_hash" not in payload
        assert "admin12345" not in payload


def test_session_cookie_and_security_headers():
    with TestClient(app) as client:
        response = client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"})
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie
        assert "samesite=lax" in cookie
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["cache-control"] == "no-store"
