"""Schemas package."""

from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserResponse,
)
from app.schemas.course import (
    CourseCreate,
    CourseDetailResponse,
    CourseJoinRequest,
    CourseMemberResponse,
    CourseResponse,
    EnrollmentResponse,
)
from app.schemas.lab import (
    LabDashboardResponse,
    LabDashboardStudent,
    LabProblemItem,
    LabSessionCreate,
    LabSessionDetailResponse,
    LabSessionResponse,
    StudentLabProgressResponse,
)
from app.schemas.problem import (
    BulkImportRequest,
    BulkImportResponse,
    ProblemCreate,
    ProblemDetail,
    ProblemSummary,
    ProblemUpdate,
    TestCaseCreate,
    TestCaseSummary,
)
from app.schemas.submission import (
    GradebookProblemHeader,
    GradebookResponse,
    GradebookScoreItem,
    GradebookStudentRow,
    RunRequest,
    SubmissionCreated,
    SubmissionResponse,
    SubmissionSummaryResponse,
    SubmitRequest,
    TestCaseResult,
)

__all__ = [
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "UserResponse",
    "TokenResponse",
    "TokenRefreshResponse",
    "AuthResponse",
    # Courses
    "CourseCreate",
    "CourseResponse",
    "CourseDetailResponse",
    "CourseJoinRequest",
    "EnrollmentResponse",
    "CourseMemberResponse",
    # Labs
    "LabSessionCreate",
    "LabSessionResponse",
    "LabSessionDetailResponse",
    "LabProblemItem",
    "LabDashboardStudent",
    "LabDashboardResponse",
    "StudentLabProgressResponse",
    # Problems
    "TestCaseCreate",
    "TestCaseSummary",
    "ProblemCreate",
    "ProblemUpdate",
    "ProblemSummary",
    "ProblemDetail",
    "BulkImportRequest",
    "BulkImportResponse",
    # Submissions
    "RunRequest",
    "SubmitRequest",
    "SubmissionCreated",
    "SubmissionResponse",
    "SubmissionSummaryResponse",
    "TestCaseResult",
    "GradebookProblemHeader",
    "GradebookScoreItem",
    "GradebookStudentRow",
    "GradebookResponse",
]
