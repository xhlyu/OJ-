import asyncio
from types import SimpleNamespace

from app.judge.runner import run_judge
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
