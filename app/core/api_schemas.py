from pydantic import BaseModel, Field
from typing import List
from app.core.schemas import CandidateProfile


class MatchRequest(BaseModel):
    job_description: str = Field(
        ...,
        min_length=10,
        description="The raw text description of the target role requirement.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of ranked candidates to return.",
    )


class CandidateRankResponse(BaseModel):
    candidate_id: int
    filename: str
    name: str
    fit_score: int
    justification: str


class MatchResponse(BaseModel):
    job_description: str
    results: List[CandidateRankResponse]


class UploadResponse(BaseModel):
    message: str
    resume_id: int
    filename: str
    profile: CandidateProfile
