from typing import List, Optional
from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    company: str = Field(description="Name of the company or organization")
    role: str = Field(description="Job title or role held")
    duration: str = Field(
        description="Timeframe spent at the company (e.g., Jan 2021 - Present)"
    )
    responsibilities: List[str] = Field(
        description="Key bullet points or responsibilities managed"
    )


class Education(BaseModel):
    institution: str = Field(description="Name of the school, university, or boot camp")
    degree: str = Field(
        description="Degree or certificate earned (e.g., Bachelor of Science in CS)"
    )
    graduation_year: Optional[str] = Field(
        None, description="Year of graduation if visible"
    )


class CandidateProfile(BaseModel):
    full_name: str = Field(description="Candidate's full name")
    email: Optional[str] = Field(None, description="Extracted email address")
    skills: List[str] = Field(
        description="List of technical and soft skills highlighted in the resume"
    )
    experience_level: str = Field(
        description="Overall senior level classification: Junior, Mid, Senior, Lead, or Executive"
    )
    work_history: List[WorkExperience] = Field(
        description="Chronological work historical summaries"
    )
    education_history: List[Education] = Field(
        description="Educational baseline records"
    )
