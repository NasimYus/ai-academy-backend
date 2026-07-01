from pydantic import BaseModel


class PrerequisiteInput(BaseModel):
    prerequisite_id: int
    required: bool = False


class PrerequisiteRead(BaseModel):
    id: int
    prerequisite_id: int
    title: str
    required: bool


class RelatedInput(BaseModel):
    related_id: int


class RelatedRead(BaseModel):
    id: int
    related_id: int
    title: str
