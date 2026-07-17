import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import BACKUP_DIR, LOG_TEXT_LIMIT
from app.main import app
from app.models import JudgeLog
from app.serializers import log_view
from app.utils import sanitize_error, truncate_text


def login_admin(client: TestClient) -> None:
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"}).status_code == 200


def test_log_truncation_path_sanitization_and_hidden_view():
    long_text = "x" * (LOG_TEXT_LIMIT + 100)
    assert len(truncate_text(long_text)) == LOG_TEXT_LIMIT
    assert truncate_text(long_text).endswith("...[truncated]")
    assert "C:\\oj\\temp" not in sanitize_error(r"Traceback C:\oj\temp\submission\main.py line 3")
    assert "/home/server" not in sanitize_error("Traceback /home/server/oj/temp/main.py line 3")
    log = JudgeLog(case_id="hidden", result="WA", score=0, time_used=0.1, exit_code=0,
                   input_data="secret input", stdout="secret actual", stderr="", expected_output="secret answer",
                   message="wrong answer", is_hidden=True, submission_id="submission")
    student = log_view(log, False)
    assert "input_data" not in student
    assert "stdout" not in student
    assert "expected_output" not in student
    teacher = log_view(log, True)
    assert teacher["input_data"] == "secret input"
    assert teacher["expected_output"] == "secret answer"


def test_corrupt_backup_does_not_damage_current_data():
    backup_id = f"backup_corrupt_{time.time_ns()}"
    folder = BACKUP_DIR / backup_id
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(json.dumps({"storage": "sqlite", "files": ["oj.db"]}), encoding="utf-8")
    (folder / "oj.db").write_bytes(b"not a sqlite database")
    try:
        with TestClient(app) as admin_client:
            login_admin(admin_client)
            before = admin_client.get("/api/auth/me").json()["data"]["username"]
            restored = admin_client.post(f"/api/admin/backups/{backup_id}/restore")
            assert restored.status_code == 400
            assert admin_client.get("/api/auth/me").json()["data"]["username"] == before
            audits = admin_client.get("/api/audit-logs", params={"target_id": backup_id}).json()["data"]["items"]
            assert audits[0]["action"] == "RESTORE_BACKUP"
            assert audits[0]["success"] is False
    finally:
        for item in folder.iterdir():
            item.unlink()
        folder.rmdir()


def test_backup_restore_rolls_back_new_user():
    username = f"afterbackup{time.time_ns() % 100000000}"
    with TestClient(app) as admin_client:
        login_admin(admin_client)
        created = admin_client.post("/api/admin/backups")
        backup_id = created.json()["data"]["backup_id"]
        assert admin_client.post("/api/auth/register", json={"username": username, "password": "password123"}).status_code == 201
        users_before_restore = admin_client.get("/api/users", params={"username": username}).json()["data"]["items"]
        assert any(item["username"] == username for item in users_before_restore)
        restored = admin_client.post(f"/api/admin/backups/{backup_id}/restore")
        assert restored.status_code == 200
        users_after_restore = admin_client.get("/api/users", params={"username": username}).json()["data"]["items"]
        assert all(item["username"] != username for item in users_after_restore)
        audits = admin_client.get("/api/audit-logs", params={"action": "RESTORE_BACKUP", "target_id": backup_id}).json()["data"]["items"]
        assert audits[0]["success"] is True


def test_tampered_backup_is_rejected_by_checksum():
    with TestClient(app) as admin_client:
        login_admin(admin_client)
        created = admin_client.post("/api/admin/backups")
        backup_id = created.json()["data"]["backup_id"]
        database_file = BACKUP_DIR / backup_id / "oj.db"
        original = database_file.read_bytes()
        database_file.write_bytes(original + b"tampered")
        try:
            restored = admin_client.post(f"/api/admin/backups/{backup_id}/restore")
            assert restored.status_code == 400
            assert "checksum mismatch" in restored.json()["message"]
            audits = admin_client.get("/api/audit-logs", params={"target_id": backup_id}).json()["data"]["items"]
            assert audits[0]["success"] is False
        finally:
            database_file.write_bytes(original)
