from fastapi.testclient import TestClient

from app.database import engine
from app.main import app


def test_health_endpoint_and_security_headers():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["data"] == {"status": "healthy", "storage": "sqlite"}
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"


def test_sqlite_foreign_keys_are_enabled():
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one().lower() == "wal"


def test_pytest_uses_isolated_database():
    assert "pytest-runtime" in str(engine.url.database)
