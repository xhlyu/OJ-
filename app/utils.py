from __future__ import annotations

from datetime import datetime, timezone
import re

from fastapi.responses import JSONResponse

from app.config import LOG_TEXT_LIMIT


def response(data=None, message: str = "ok", status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": status_code, "message": message, "data": data})


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def truncate_text(value: str) -> str:
    if len(value) <= LOG_TEXT_LIMIT:
        return value
    return value[: LOG_TEXT_LIMIT - 14] + "...[truncated]"


def sanitize_error(value: str) -> str:
    value = re.sub(r"(?:[A-Za-z]:\\|/)(?:[^\s:\n]+[/\\])+main\.py", "<submission>/main.py", value)
    return truncate_text(value)


def normalize_output(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in value.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
