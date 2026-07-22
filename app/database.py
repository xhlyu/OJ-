from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_PATH, ensure_directories


ensure_directories()
engine = create_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def ensure_schema_compatibility() -> None:
    """Add columns introduced after the first SQLite database was created."""
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(problems)"))}
        if "judge_mode" not in columns:
            connection.execute(text(
                "ALTER TABLE problems ADD COLUMN judge_mode VARCHAR(16) NOT NULL DEFAULT 'standard'"
            ))
        if "checker_code" not in columns:
            connection.execute(text("ALTER TABLE problems ADD COLUMN checker_code TEXT"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
