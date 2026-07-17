from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import admin
from app.config import BACKUP_DIR, DATABASE_PATH
from app.database import engine, get_db
from app.models import AuditLog, Backup, User
from app.utils import iso, response

router = APIRouter()


@router.get("/audit-logs")
async def audit_logs(operator_id: str | None = None, action: str | None = None, target_id: str | None = None,
                     _: User = Depends(admin), db: Session = Depends(get_db)):
    query = select(AuditLog)
    if operator_id: query = query.where(AuditLog.operator_id == operator_id)
    if action: query = query.where(AuditLog.action == action)
    if target_id: query = query.where(AuditLog.target_id == target_id)
    items = db.scalars(query.order_by(AuditLog.created_at.desc())).all()
    return response({"items": [{"id": x.id, "operator_id": x.operator_id, "action": x.action,
                                "target_type": x.target_type, "target_id": x.target_id,
                                "success": x.success, "detail": x.detail, "created_at": iso(x.created_at)} for x in items]})


@router.post("/admin/backups")
async def create_backup(operator: User = Depends(admin), db: Session = Depends(get_db)):
    backup_id = datetime.now(timezone.utc).strftime("backup_%Y%m%d_%H%M%S_%f")
    folder = BACKUP_DIR / backup_id; folder.mkdir(parents=True)
    target = folder / "oj.db"
    source_conn = sqlite3.connect(DATABASE_PATH)
    target_conn = sqlite3.connect(target)
    try: source_conn.backup(target_conn)
    finally: source_conn.close(); target_conn.close()
    manifest = {"backup_id": backup_id, "created_at": datetime.now(timezone.utc).isoformat(),
                "storage": "sqlite", "files": ["oj.db"]}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    db.add(Backup(id=backup_id)); db.add(AuditLog(operator_id=operator.id, action="CREATE_BACKUP", target_type="backup", target_id=backup_id)); db.commit()
    return response({"backup_id": backup_id, "created_at": manifest["created_at"]}, "backup created", 201)


@router.get("/admin/backups")
async def list_backups(_: User = Depends(admin), db: Session = Depends(get_db)):
    items = db.scalars(select(Backup).order_by(Backup.created_at.desc())).all()
    return response({"items": [{"backup_id": x.id, "created_at": iso(x.created_at)} for x in items]})


@router.post("/admin/backups/{backup_id}/restore")
async def restore_backup(backup_id: str, operator: User = Depends(admin), db: Session = Depends(get_db)):
    if not backup_id.startswith("backup_") or any(x in backup_id for x in ("/", "\\", "..")):
        raise HTTPException(400, "invalid backup id")
    folder = BACKUP_DIR / backup_id; manifest_path = folder / "manifest.json"; source = folder / "oj.db"
    if not manifest_path.is_file() or not source.is_file(): raise HTTPException(404, "backup not found")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("storage") != "sqlite" or "oj.db" not in manifest.get("files", []): raise ValueError("invalid manifest")
        check = sqlite3.connect(source); check.execute("PRAGMA quick_check").fetchone(); check.close()
    except Exception as exc:
        raise HTTPException(400, f"invalid backup: {exc}")
    safety = DATABASE_PATH.with_suffix(".restore-safety")
    engine.dispose(); shutil.copy2(DATABASE_PATH, safety)
    try:
        shutil.copy2(source, DATABASE_PATH)
        safety.unlink(missing_ok=True)
    except Exception:
        shutil.copy2(safety, DATABASE_PATH); safety.unlink(missing_ok=True); raise HTTPException(500, "restore failed")
    return response({"backup_id": backup_id}, "backup restored")
