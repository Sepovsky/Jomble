from pydantic import BaseModel, Field


class MatchResponse(BaseModel):
    score: float
    matched: list[str]
    missing: list[str]
    resume_extra: list[str]
    job_skill_count: int
    resume_skill_count: int
    summary: str
    job_text: str = ""
    # User preference gate (job vs stated metadata)
    metadata_satisfied: bool = True
    metadata_blockers: list[str] = Field(default_factory=list)
    metadata_warnings: list[str] = Field(default_factory=list)
    metadata_summary: str = ""
    metadata_match_skipped: bool = False
    metadata_skipped: bool = False
