from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Shape of FastAPI's default HTTPException body (`{"detail": "..."}`).

    Declared on routes via `responses=` so the error contract is part of the
    OpenAPI schema and the generated frontend client types `error` honestly.
    """

    detail: str


def error_responses(*status_codes: int) -> dict[int | str, dict[str, type[ErrorResponse]]]:
    """Build a FastAPI `responses=` map documenting the given error codes."""
    return {code: {"model": ErrorResponse} for code in status_codes}
