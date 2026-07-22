from fastapi.testclient import TestClient

from app.main import app


def test_demo_problems_are_seeded_and_listed_first():
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"})
        items = client.get("/api/problems", params={"page_size": 100}).json()["data"]["items"]
        ids = [item["id"] for item in items]
        assert ids[:3] == ["DEMO_A_PLUS_B", "DEMO_MAX_OF_THREE", "DEMO_SUM_1_TO_N"]
        detail = client.get("/api/problems/DEMO_A_PLUS_B").json()["data"]
        assert detail["title"] == "A+B 问题"
        assert "给定两个整数" in detail["description"]
        assert sum(case["score"] for case in detail["test_cases"]) == 100


def test_frontend_contains_readable_problem_detail_fields():
    html = open("frontend/index.html", encoding="utf-8").read()
    for text in ("题目描述", "输入说明", "输出说明", "数据范围", "detailSamples", "开始作答"):
        assert text in html
    assert 'id="messagePanel"' in html
    assert 'message-panel" hidden' in html
    assert "hideMessage(); await me()" in html


def test_frontend_has_structured_teacher_problem_editor():
    html = open("frontend/index.html", encoding="utf-8").read()
    for text in (
        "教师端：编程题目管理", "teacherProblemId", "teacherProblemTitle",
        "sampleEditors", "testCaseEditors", "增加样例", "增加测试点",
        "createProblemFromForm", "updateProblemFromForm", "deleteProblemFromForm",
        "测试点总分必须等于 100",
    ):
        assert text in html
    assert 'id="problemJson"' not in html
