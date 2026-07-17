from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
import time
import uuid
from typing import Optional

from app.config import TEMP_DIR
from app.utils import normalize_output, sanitize_error, truncate_text


@dataclass
class CaseResult:
    case_id: str
    result: str
    score: int
    time_used: float
    exit_code: Optional[int]
    input_data: str
    stdout: str
    stderr: str
    expected_output: str
    message: str
    is_hidden: bool


async def run_judge(source_code: str, test_cases, time_limit: float) -> tuple[str, int, float, list[CaseResult]]:
    run_dir = TEMP_DIR / str(uuid.uuid4())
    run_dir.mkdir(parents=True)
    source = run_dir / "main.py"
    source.write_text(source_code, encoding="utf-8")
    results: list[CaseResult] = []
    try:
        for case in test_cases:
            started = time.perf_counter()
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, str(source), cwd=str(run_dir),
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout_b, stderr_b = await asyncio.wait_for(
                        proc.communicate(case.input_data.encode()), timeout=time_limit
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.communicate()
                    elapsed = time.perf_counter() - started
                    results.append(CaseResult(case.case_id, "TLE", 0, elapsed, None, case.input_data, "", "",
                                              case.expected_output, "time limit exceeded", case.is_hidden))
                    break
                elapsed = time.perf_counter() - started
                try:
                    stdout = stdout_b.decode("utf-8")
                    stderr = stderr_b.decode("utf-8")
                except UnicodeDecodeError:
                    results.append(CaseResult(case.case_id, "RE", 0, elapsed, proc.returncode, case.input_data, "", "",
                                              case.expected_output, "program output is not valid UTF-8", case.is_hidden))
                    break
                if proc.returncode != 0:
                    result, score, message = "RE", 0, "runtime error"
                elif normalize_output(stdout) != normalize_output(case.expected_output):
                    result, score, message = "WA", 0, "output does not match expected answer"
                else:
                    result, score, message = "AC", case.score, "accepted"
                results.append(CaseResult(case.case_id, result, score, elapsed, proc.returncode, case.input_data,
                                          truncate_text(stdout), sanitize_error(stderr), case.expected_output,
                                          message, case.is_hidden))
                if result in {"RE"}:
                    break
            except Exception as exc:
                results.append(CaseResult(case.case_id, "SE", 0, time.perf_counter() - started, None,
                                          case.input_data, "", "", case.expected_output,
                                          sanitize_error(str(exc)), case.is_hidden))
                break
        kinds = {item.result for item in results}
        final = next((kind for kind in ("SE", "TLE", "RE", "WA") if kind in kinds), "AC")
        return final, sum(item.score for item in results), sum(item.time_used for item in results), results
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
