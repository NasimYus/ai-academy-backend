from datetime import datetime

from pydantic import BaseModel, Field

from app.models.assignment import AssignmentHistoryStatus
from app.models.course import CourseType, VideoDemoSource
from app.models.quiz import QuizStatus
from app.schemas.user import UserBrief

# Instructor course create/edit — parity of WebinarsController@storeAll/updateAll.
# Tags / filters / partner-instructors are separate subsystems (deferred).


class CourseCreate(BaseModel):
    type: CourseType
    title: str = Field(min_length=1, max_length=255)
    thumbnail: str
    image_cover: str
    description: str
    category_id: int
    duration: int | None = None

    # webinar-only scheduling (legacy required_if:type,webinar)
    start_date: datetime | None = None
    capacity: int | None = None

    seo_description: str | None = None
    video_demo: str | None = None
    video_demo_source: VideoDemoSource | None = None
    price: float = 0
    organization_price: float | None = None
    points: int | None = None
    access_days: int | None = None

    private: bool = False
    support: bool = False
    downloadable: bool = False
    partner_instructor: bool = False
    subscribe: bool = False

    # T&C accepted (legacy `rules` == 1); when false the course stays a draft.
    rules: bool = False
    # explicit "save as draft" (legacy `draft`/`get_next`)
    draft: bool = False


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    type: CourseType | None = None
    thumbnail: str | None = None
    image_cover: str | None = None
    description: str | None = None
    category_id: int | None = None
    duration: int | None = None
    start_date: datetime | None = None
    capacity: int | None = None
    seo_description: str | None = None
    video_demo: str | None = None
    video_demo_source: VideoDemoSource | None = None
    price: float | None = None
    organization_price: float | None = None
    points: int | None = None
    access_days: int | None = None
    private: bool | None = None
    support: bool | None = None
    downloadable: bool | None = None
    partner_instructor: bool | None = None
    subscribe: bool | None = None


# Instructor quiz CRUD — parity of Instructor\QuizzesController.
# The questions themselves are managed separately (web panel); these endpoints
# manage the quiz shell + the results dashboard.


class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    course_id: int  # legacy webinar_id; required here (our quizzes belong to a course)
    chapter_id: int | None = None
    pass_mark: int = Field(ge=0)
    attempt: int | None = Field(default=None, ge=1)
    time: int | None = Field(default=None, ge=0)
    active: bool = False
    certificate: bool = False


class QuizUpdate(QuizCreate):
    pass


class QuizManageRead(BaseModel):
    id: int
    title: str
    course_id: int
    chapter_id: int | None
    pass_mark: int
    attempt: int | None
    time: int
    status: QuizStatus
    certificate: bool
    created_at: datetime


class QuizResultRow(BaseModel):
    id: int
    user: UserBrief | None
    quiz_id: int
    quiz_title: str
    user_grade: int | None
    status: str
    created_at: datetime


class QuizResultsOverview(BaseModel):
    quiz_results_count: int
    passed_count: int
    waiting_count: int
    success_rate: int
    avg_grade: float
    quizzes: list[QuizManageRead]
    results: list[QuizResultRow]


# Instructor assignment grading — parity of Instructor\AssignmentController.


class AssignmentHistoryRow(BaseModel):
    id: int
    student: UserBrief | None
    status: AssignmentHistoryStatus
    grade: int | None
    submissions_count: int
    created_at: datetime


class InstructorAssignmentRow(BaseModel):
    id: int
    title: str
    course_id: int
    pass_grade: int | None
    histories: list[AssignmentHistoryRow]


class AssignmentDashboard(BaseModel):
    course_assignments_count: int
    pending_reviews_count: int
    passed_count: int
    failed_count: int
    assignments: list[InstructorAssignmentRow]


class SubmissionMessage(BaseModel):
    id: int
    sender: UserBrief | None
    message: str
    file_title: str | None
    file_path: str | None
    created_at: datetime


class SubmissionView(BaseModel):
    id: int
    student: UserBrief | None
    status: AssignmentHistoryStatus
    grade: int | None
    messages: list[SubmissionMessage]


class GradeInput(BaseModel):
    grade: int


class CommentReplyInput(BaseModel):
    reply: str = Field(min_length=1)


# Instructor course statistics — parity of WebinarStatisticController (statistic=true).


class CourseStatistics(BaseModel):
    students_count: int
    sales_count: int
    sales_amount: float
    rate: float
    reviews_count: int
    comments_count: int
    chapters_count: int
    sessions_count: int
    files_count: int
    text_lessons_count: int
    quizzes_count: int
    assignments_count: int
    forums_count: int
