"""ORM models package — import all models here so Alembic and SQLAlchemy detect them."""

from app.models.badge import Badge
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.exam import Exam, ExamProblem
from app.models.exam_session import ExamSession
from app.models.exam_violation import ExamViolation
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.learning_content import LearningContent
from app.models.learning_module import LearningModule
from app.models.module_progress import ModuleProgress
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
    "LearningModule",
    "LearningContent",
    "ModuleProgress",
    "Exam",
    "ExamProblem",
    "ExamSession",
    "ExamViolation",
]
