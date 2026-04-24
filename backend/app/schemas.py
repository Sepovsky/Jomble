from pydantic import BaseModel


class MatchResponse(BaseModel):
    score: float
    matched: list[str]
    missing: list[str]
    resume_extra: list[str]
    job_skill_count: int
    resume_skill_count: int
    summary: str
