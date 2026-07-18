from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import shutil
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import admin
from app.config import BACKUP_DIR, DATABASE_PATH
from app.database import SessionLocal, engine, get_db
from app.models import AuditLog, Backup, User
from app.utils import iso, response, validate_time_range

router = APIRouter()


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remove_sqlite_sidecars(database_path) -> None:
    for suffix in ("-wal", "-shm"):
        database_path.with_name(database_path.name + suffix).unlink(missing_ok=True)


def sqlite_copy(source_path, target_path) -> None:
    source_conn = sqlite3.connect(source_path)
    target_conn = sqlite3.connect(target_path)
    try:
        source_conn.backup(target_conn)
    finally:
        source_conn.close()
        target_conn.close()


def write_restore_audit(operator_id: str, backup_id: str, success: bool, detail: str | None = None) -> None:
    with SessionLocal() as audit_db:
        audit_db.add(AuditLog(operator_id=operator_id, action="RESTORE_BACKUP", target_type="backup",
                              target_id=backup_id, success=success, detail=detail))
        audit_db.commit()


@router.get("/audit-logs")
async def audit_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     operator_id: str | None = None, action: str | None = None, target_id: str | None = None,
                     start_time: datetime | None = None, end_time: datetime | None = None,
                     _: User = Depends(admin), db: Session = Depends(get_db)):
    validate_time_range(start_time, end_time)
    query = select(AuditLog)
    if operator_id: query = query.where(AuditLog.operator_id == operator_id)
    if action: query = query.where(AuditLog.action == action)
    if target_id: query = query.where(AuditLog.target_id == target_id)
    if start_time: query = query.where(AuditLog.created_at >= start_time)
    if end_time: query = query.where(AuditLog.created_at <= end_time)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return response({"items": [{"id": x.id, "operator_id": x.operator_id, "action": x.action,
                                "target_type": x.target_type, "target_id": x.target_id,
                                "success": x.success, "detail": x.detail, "created_at": iso(x.created_at)} for x in items],
                     "total": total, "page": page, "page_size": page_size})


@router.post("/admin/backups")
async def create_backup(operator: User = Depends(admin), db: Session = Depends(get_db)):
    backup_id = datetime.now(timezone.utc).strftime("backup_%Y%m%d_%H%M%S_%f")
    created_at = datetime.now(timezone.utc)
    db.add(Backup(id=backup_id, created_at=created_at))
    db.add(AuditLog(operator_id=operator.id, action="CREATE_BACKUP", target_type="backup", target_id=backup_id))
    db.commit()
    folder = BACKUP_DIR / backup_id
    folder.mkdir(parents=True)
    target = folder / "oj.db"
    try:
        sqlite_copy(DATABASE_PATH, target)
        manifest = {
            "backup_id": backup_id,
            "created_at": created_at.isoformat(),
            "storage": "sqlite",
            "files": ["oj.db"],
            "sha256": {"oj.db": file_sha256(target)},
        }
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        backup = db.get(Backup, backup_id)
        if backup:
            db.delete(backup)
        db.add(AuditLog(operator_id=operator.id, action="CREATE_BACKUP", target_type="backup",
                        target_id=backup_id, success=False, detail=str(exc)))
        db.commit()
        raise HTTPException(500, "backup creation failed") from exc
    return response({"backup_id": backup_id, "created_at": manifest["created_at"]}, "backup created", 201)


@router.get("/admin/backups")
async def list_backups(_: User = Depends(admin), db: Session = Depends(get_db)):
    items = db.scalars(select(Backup).order_by(Backup.created_at.desc())).all()
    return response({"items": [{"backup_id": x.id, "created_at": iso(x.created_at)} for x in items]})


@router.post("/admin/backups/{backup_id}/restore")
async def restore_backup(backup_id: str, operator: User = Depends(admin), db: Session = Depends(get_db)):
    if not backup_id.startswith("backup_") or any(x in backup_id for x in ("/", "\\", "..")):
        write_restore_audit(operator.id, backup_id, False, "invalid backup id")
        raise HTTPException(400, "invalid backup id")
    folder = BACKUP_DIR / backup_id
    manifest_path = folder / "manifest.json"
    source = folder / "oj.db"
    if not manifest_path.is_file() or not source.is_file():
        write_restore_audit(operator.id, backup_id, False, "backup not found")
        raise HTTPException(404, "backup not found")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("backup_id") != backup_id:
            raise ValueError("backup id does not match manifest")
        if manifest.get("storage") != "sqlite" or "oj.db" not in manifest.get("files", []):
            raise ValueError("invalid manifest")
        expected_hash = manifest.get("sha256", {}).get("oj.db")
        if not expected_hash or file_sha256(source) != expected_hash:
            raise ValueError("backup checksum mismatch")
        check = sqlite3.connect(source)
        try:
            check_result = check.execute("PRAGMA quick_check").fetchone()
        finally:
            check.close()
        if not check_result or check_result[0] != "ok":
            raise ValueError("database integrity check failed")
    except Exception as exc:
        write_restore_audit(operator.id, backup_id, False, str(exc))
        raise HTTPException(400, f"invalid backup: {exc}")
    safety = DATABASE_PATH.with_suffix(".restore-safety")
    db.close()
    engine.dispose()
    safety.unlink(missing_ok=True)
    sqlite_copy(DATABASE_PATH, safety)
    try:
        remove_sqlite_sidecars(DATABASE_PATH)
        shutil.copy2(source, DATABASE_PATH)
        safety.unlink(missing_ok=True)
    except Exception:
        remove_sqlite_sidecars(DATABASE_PATH)
        shutil.copy2(safety, DATABASE_PATH)
        safety.unlink(missing_ok=True)
        write_restore_audit(operator.id, backup_id, False, "database replacement failed")
        raise HTTPException(500, "restore failed")
    write_restore_audit(operator.id, backup_id, True)
    return response({"backup_id": backup_id}, "backup restored")
