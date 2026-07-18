import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import User


def test_all_fastapi_routes_are_async():
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith(("@router.get", "@router.post", "@router.put", "@router.delete", "@app.get")):
                next_line = next(item.strip() for item in lines[index + 1:] if item.strip())
                assert next_line.startswith("async def "), f"route in {path}:{index + 1} must use async def"


def test_time_range_validation():
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"})
        start = datetime.now(timezone.utc)
        end = start - timedelta(days=1)
        params = {"start_time": start.isoformat(), "end_time": end.isoformat()}
        assert client.get("/api/submissions", params=params).status_code == 400
        assert client.get("/api/logs", params=params).status_code == 400
        assert client.get("/api/audit-logs", params=params).status_code == 400


def test_submission_filters_and_pagination_shape():
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"})
        response = client.get("/api/submissions", params={"page": 1, "page_size": 5, "status": "finished"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["page"] == 1 and data["page_size"] == 5
        assert len(data["items"]) <= 5
        assert all(item["status"] == "finished" for item in data["items"])


def test_database_persistence_across_app_lifespans():
    username = f"persistent{time.time_ns() % 100000000}"
    with TestClient(app) as client:
        assert client.post("/api/auth/register", json={"username": username, "password": "password123"}).status_code == 201
    with TestClient(app) as restarted_client:
        assert restarted_client.post("/api/auth/login", json={"username": username, "password": "password123"}).status_code == 200
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).one()
        db.delete(user)
        db.commit()
