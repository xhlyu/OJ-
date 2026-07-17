import json

from sqlalchemy.orm import Session

from app.models import Problem, TestCase


DEMO_PROBLEMS = [
    {
        "id": "DEMO_A_PLUS_B", "title": "A+B 问题", "difficulty": "easy", "tags": ["演示题", "基础", "输入输出"],
        "description": "给定两个整数 a 和 b，请计算并输出它们的和。",
        "input_description": "一行包含两个整数 a 和 b，以空格分隔。",
        "output_description": "输出一个整数，表示 a+b。", "constraints": "-10^9 <= a, b <= 10^9",
        "samples": [{"input": "1 2\n", "output": "3\n"}], "time_limit": 1.0, "memory_limit": 128,
        "test_cases": [("sample", "1 2\n", "3\n", 30, False), ("negative", "-10 3\n", "-7\n", 30, True), ("large", "1000000000 1000000000\n", "2000000000\n", 40, True)],
    },
    {
        "id": "DEMO_MAX_OF_THREE", "title": "三个数中的最大值", "difficulty": "easy", "tags": ["演示题", "条件判断"],
        "description": "输入三个整数，输出其中最大的一个。",
        "input_description": "一行包含三个整数，以空格分隔。",
        "output_description": "输出三个整数中的最大值。", "constraints": "-10^6 <= 数值 <= 10^6",
        "samples": [{"input": "3 8 5\n", "output": "8\n"}], "time_limit": 1.0, "memory_limit": 128,
        "test_cases": [("sample", "3 8 5\n", "8\n", 30, False), ("negative", "-3 -8 -5\n", "-3\n", 30, True), ("equal", "7 7 7\n", "7\n", 40, True)],
    },
    {
        "id": "DEMO_SUM_1_TO_N", "title": "1 到 N 的整数和", "difficulty": "easy", "tags": ["演示题", "循环", "数学"],
        "description": "给定正整数 N，计算 1+2+...+N。",
        "input_description": "输入一个正整数 N。", "output_description": "输出 1 到 N 的整数和。",
        "constraints": "1 <= N <= 100000", "samples": [{"input": "5\n", "output": "15\n"}],
        "time_limit": 1.0, "memory_limit": 128,
        "test_cases": [("sample", "5\n", "15\n", 30, False), ("one", "1\n", "1\n", 30, True), ("large", "100000\n", "5000050000\n", 40, True)],
    },
]


def seed_demo_problems(db: Session) -> None:
    for data in DEMO_PROBLEMS:
        if db.get(Problem, data["id"]):
            continue
        problem = Problem(id=data["id"], title=data["title"], description=data["description"],
                          input_description=data["input_description"], output_description=data["output_description"],
                          samples_json=json.dumps(data["samples"], ensure_ascii=False), constraints=data["constraints"],
                          time_limit=data["time_limit"], memory_limit=data["memory_limit"], difficulty=data["difficulty"],
                          tags_json=json.dumps(data["tags"], ensure_ascii=False))
        problem.test_cases = [TestCase(case_id=case_id, input_data=input_data, expected_output=output,
                                       score=score, is_hidden=hidden)
                              for case_id, input_data, output, score, hidden in data["test_cases"]]
        db.add(problem)
    db.commit()
