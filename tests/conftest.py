import os
from pathlib import Path
import shutil


TEST_RUNTIME = Path(__file__).resolve().parent.parent / "work" / "pytest-runtime"
shutil.rmtree(TEST_RUNTIME, ignore_errors=True)
TEST_RUNTIME.mkdir(parents=True, exist_ok=True)

# These variables must be set before application modules are imported.
os.environ["OJ_DATA_DIR"] = str(TEST_RUNTIME / "data")
os.environ["OJ_TEMP_DIR"] = str(TEST_RUNTIME / "temp")
os.environ["OJ_BACKUP_DIR"] = str(TEST_RUNTIME / "backups")
os.environ["OJ_DATABASE_PATH"] = str(TEST_RUNTIME / "data" / "test.db")
os.environ["OJ_SESSION_SECRET"] = "pytest-session-secret"


def pytest_sessionfinish(session, exitstatus):
    try:
        from app.database import engine

        engine.dispose()
    except ImportError:
        pass
    shutil.rmtree(TEST_RUNTIME, ignore_errors=True)
