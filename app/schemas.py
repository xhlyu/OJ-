import ast
from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_must_not_have_outer_whitespace(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("username cannot start or end with whitespace")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("username may only contain letters, numbers, underscores, and hyphens")
        return value

    @field_validator("password")
    @classmethod
    def password_must_fit_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must not exceed 72 UTF-8 bytes")
        if not re.search(r"[A-Za-z]", value) or not re.search(r"[0-9]", value):
            raise ValueError("password must contain at least one letter and one number")
        return value


class UserUpdate(BaseModel):
    role: Literal["student", "teacher", "admin"]
    is_active: bool


class Sample(BaseModel):
    input: str
    output: str


class TestCaseIn(BaseModel):
    case_id: str = Field(min_length=1, max_length=64)
    input: str
    output: str
    score: int = Field(ge=0)
    is_hidden: bool = True


class ProblemIn(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    input_description: str = Field(min_length=1)
    output_description: str = Field(min_length=1)
    samples: list[Sample] = Field(min_length=1)
    constraints: str = ""
    time_limit: float = Field(gt=0)
    memory_limit: int = Field(gt=0)
    difficulty: Literal["easy", "medium", "hard"]
    tags: list[str] = []
    judge_mode: Literal["standard", "special"] = "standard"
    checker_code: str | None = Field(default=None, max_length=32768)
    test_cases: list[TestCaseIn] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_problem(self):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.id):
            raise ValueError("invalid problem id")
        ids = [case.case_id for case in self.test_cases]
        if len(ids) != len(set(ids)):
            raise ValueError("case_id must be unique")
        if sum(case.score for case in self.test_cases) != 100:
            raise ValueError("test case scores must sum to 100")
        if self.judge_mode == "special":
            if not self.checker_code or not self.checker_code.strip():
                raise ValueError("special judge requires checker_code")
            try:
                tree = ast.parse(self.checker_code)
            except SyntaxError as exc:
                raise ValueError(f"checker_code syntax error: {exc.msg}") from exc
            if not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "check"
                       for node in tree.body):
                raise ValueError("checker_code must define check(input_data, expected_output, actual_output)")
            if any(isinstance(node, ast.AsyncFunctionDef) and node.name == "check" for node in tree.body):
                raise ValueError("checker check function must be synchronous")
        else:
            self.checker_code = None
        return self


class SubmissionIn(BaseModel):
    problem_id: str
    language: Literal["python"] = "python"
    source_code: str = Field(min_length=1)

    @field_validator("source_code")
    @classmethod
    def source_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_code cannot be blank")
        return value


class Page(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
