from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserBrief


class ForumCan(BaseModel):
    pin: bool = False
    update: bool = False
    resolve: bool = False


class LastAnswer(BaseModel):
    description: str
    user: UserBrief | None = None


class ForumThreadRead(BaseModel):
    id: int
    title: str
    description: str
    pin: bool
    attachment: str | None = None
    answers_count: int
    resolved: bool
    user: UserBrief | None = None
    created_at: datetime
    can: ForumCan
    # present only when the thread has answers (legacy mergeWhen)
    active_users: list[str] | None = None
    more: int | None = None
    last_activity: datetime | None = None
    last_answer: LastAnswer | None = None


class ForumAnswerRead(BaseModel):
    id: int
    description: str
    pin: bool
    resolved: bool
    user: UserBrief | None = None
    created_at: datetime
    can: ForumCan


class ForumListResponse(BaseModel):
    forums: list[ForumThreadRead]
    questions_count: int
    resolved_count: int
    open_questions_count: int
    comments_count: int
    active_users_count: int


class ForumThreadInput(BaseModel):
    title: str
    description: str


class ForumAnswerInput(BaseModel):
    description: str
