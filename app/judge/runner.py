from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
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


CHECKER_RUNNER = r'''import json
import sys

namespace = {"__builtins__": __builtins__}
try:
    with open(sys.argv[1], encoding="utf-8") as checker_file:
        exec(checker_file.read(), namespace)
    payload = json.load(sys.stdin)
    decision = namespace["check"](
        payload["input_data"], payload["expected_output"], payload["actual_output"]
    )
    if isinstance(decision, bool):
        accepted, message = decision, "accepted" if decision else "special judge rejected output"
    elif isinstance(decision, (tuple, list)) and len(decision) == 2 and isinstance(decision[0], bool):
        accepted, message = decision[0], str(decision[1])
    else:
        raise TypeError("check must return bool or (bool, message)")
    print(json.dumps({"accepted": accepted, "message": message}))
except Exception as exc:
    print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
    sys.exit(2)
'''


async def run_special_checker(checker_path: str, input_data: str, expected_output: str,
                              actual_output: str, timeout: float, cwd: str) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-I", "-c", CHECKER_RUNNER, checker_path, cwd=cwd,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    payload = json.dumps({"input_data": input_data, "expected_output": expected_output,
                          "actual_output": actual_output}).encode()
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(payload), timeout=timeout)
    except asyncio.TimeoutError as exc:
        proc.kill()
        await proc.communicate()
        raise RuntimeError("special judge checker timed out") from exc
    if proc.returncode != 0:
        detail = stdout_b.decode("utf-8", errors="replace") or stderr_b.decode("utf-8", errors="replace")
        raise RuntimeError(f"special judge checker failed: {truncate_text(detail.strip())}")
    try:
        decision = json.loads(stdout_b.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("special judge checker returned invalid data") from exc
    if not isinstance(decision.get("accepted"), bool):
        raise RuntimeError("special judge checker returned invalid decision")
    return decision["accepted"], truncate_text(str(decision.get("message", "")))


async def run_judge(source_code: str, test_cases, time_limit: float, judge_mode: str = "standard",
                    checker_code: str | None = None) -> tuple[str, int, float, list[CaseResult]]:
    if judge_mode not in {"standard", "special"}:
        raise ValueError("unsupported judge mode")
    if judge_mode == "special" and not checker_code:
        raise ValueError("special judge checker is missing")
    run_dir = TEMP_DIR / str(uuid.uuid4())
    run_dir.mkdir(parents=True)
    source = run_dir / "main.py"
    source.write_text(source_code, encoding="utf-8")
    checker_path = run_dir / "checker.py"
    if checker_code:
        checker_path.write_text(checker_code, encoding="utf-8")
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
                else:
                    if judge_mode == "special":
                        try:
                            accepted, message = await run_special_checker(
                                str(checker_path), case.input_data, case.expected_output, stdout,
                                max(0.1, time_limit), str(run_dir),
                            )
                            result, score = ("AC", case.score) if accepted else ("WA", 0)
                        except Exception as exc:
                            result, score, message = "SE", 0, sanitize_error(str(exc))
                    elif normalize_output(stdout) != normalize_output(case.expected_output):
                        result, score, message = "WA", 0, "output does not match expected answer"
                    else:
                        result, score, message = "AC", case.score, "accepted"
                results.append(CaseResult(case.case_id, result, score, elapsed, proc.returncode, case.input_data,
                                          truncate_text(stdout), sanitize_error(stderr), case.expected_output,
                                          message, case.is_hidden))
                if result in {"RE", "SE"}:
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
