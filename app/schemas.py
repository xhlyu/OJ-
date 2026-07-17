from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


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
        return self


class SubmissionIn(BaseModel):
    problem_id: str
    language: Literal["python"] = "python"
    source_code: str = Field(min_length=1)


class Page(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
