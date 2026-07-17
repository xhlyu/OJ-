from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("OJ_DATA_DIR", BASE_DIR / "data"))
TEMP_DIR = Path(os.getenv("OJ_TEMP_DIR", BASE_DIR / "temp"))
BACKUP_DIR = Path(os.getenv("OJ_BACKUP_DIR", BASE_DIR / "backups"))
DATABASE_PATH = Path(os.getenv("OJ_DATABASE_PATH", DATA_DIR / "oj.db"))
SESSION_SECRET = os.getenv("OJ_SESSION_SECRET", "development-only-change-me")
ADMIN_USERNAME = os.getenv("OJ_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("OJ_ADMIN_PASSWORD", "admin12345")
MAX_SOURCE_SIZE = 64 * 1024
LOG_TEXT_LIMIT = 4000


def ensure_directories() -> None:
    for path in (DATA_DIR, TEMP_DIR, BACKUP_DIR):
        path.mkdir(parents=True, exist_ok=True)
