"""ORM models package — import all models here so Alembic and SQLAlchemy detect them."""

from app.models.badge import Badge
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.user import User

__all__ = [
    "User",
    "Course",
    "Enrollment",
    "Problem",
    "TestCase",
    "Submission",
    "LabSession",
    "LabSessionProblem",
    "Badge",
]
