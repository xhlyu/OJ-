import asyncio
from types import SimpleNamespace

from app.config import TEMP_DIR
from app.judge.runner import run_judge
import app.judge.runner as runner_module
from app.utils import normalize_output


def case(output="3\n"):
    return SimpleNamespace(case_id="c1", input_data="1 2\n", expected_output=output, score=100, is_hidden=False)


def test_output_normalization():
    assert normalize_output("3   \r\n\r\n") == "3"
    assert normalize_output(" 3\n") != normalize_output("3\n")


def test_judge_ac_wa_re_tle():
    ac = asyncio.run(run_judge("a,b=map(int,input().split());print(a+b)", [case()], 1))
    wa = asyncio.run(run_judge("print(0)", [case()], 1))
    re = asyncio.run(run_judge("print(1/0)", [case()], 1))
    tle = asyncio.run(run_judge("while True: pass", [case()], 0.1))
    assert [ac[0], wa[0], re[0], tle[0]] == ["AC", "WA", "RE", "TLE"]


def test_invalid_utf8_output_and_temp_cleanup():
    before = {path.name for path in TEMP_DIR.iterdir()}
    result = asyncio.run(run_judge("import sys; sys.stdout.buffer.write(bytes([255]))", [case()], 1))
    after = {path.name for path in TEMP_DIR.iterdir()}
    assert result[0] == "RE"
    assert "not valid UTF-8" in result[3][0].message
    assert after == before


def test_long_output_is_truncated():
    result = asyncio.run(run_judge("print('x' * 5000)", [case("x" * 5000 + "\n")], 1))
    assert result[0] == "AC"
    assert result[3][0].stdout.endswith("...[truncated]")
    assert len(result[3][0].stdout) == 4000


def test_judge_system_error(monkeypatch):
    async def fail_to_spawn(*args, **kwargs):
        raise OSError("runner unavailable")

    monkeypatch.setattr(runner_module.asyncio, "create_subprocess_exec", fail_to_spawn)
    result = asyncio.run(run_judge("print(3)", [case()], 1))
    assert result[0] == "SE"
    assert "runner unavailable" in result[3][0].message


def test_special_judge_accepts_equivalent_output_and_rejects_wrong_answer():
    checker = """def check(input_data, expected_output, actual_output):
    expected = sorted(map(int, expected_output.split()))
    actual = sorted(map(int, actual_output.split()))
    return actual == expected, 'numbers must match in any order'
"""
    accepted = asyncio.run(run_judge("print('3 2 1')", [case("1 2 3\n")], 1, "special", checker))
    rejected = asyncio.run(run_judge("print('1 2 4')", [case("1 2 3\n")], 1, "special", checker))
    assert accepted[0] == "AC" and accepted[1] == 100
    assert rejected[0] == "WA" and rejected[1] == 0
    assert rejected[3][0].message == "numbers must match in any order"


def test_special_judge_checker_failure_becomes_system_error():
    checker = """def check(input_data, expected_output, actual_output):
    raise RuntimeError('broken checker')
"""
    result = asyncio.run(run_judge("print(3)", [case()], 1, "special", checker))
    assert result[0] == "SE"
    assert "broken checker" in result[3][0].message


def test_special_judge_checker_can_import_modules():
    checker = """import math
def check(input_data, expected_output, actual_output):
    return math.isclose(float(expected_output), float(actual_output), rel_tol=1e-6)
"""
    result = asyncio.run(run_judge("print('3.000001')", [case("3.0\n")], 1, "special", checker))
    assert result[0] == "AC"
