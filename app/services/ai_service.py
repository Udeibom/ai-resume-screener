import asyncio
import os
from typing import Callable, List, TypeVar

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.schemas import CandidateProfile

load_dotenv()

T = TypeVar("T")


class CandidateEvaluation(BaseModel):
    fit_score: int = Field(
        ge=0,
        le=100,
        description="Overall candidate fit score."
    )

    justification: str


class AIService:
    """
    Centralized Gemini service.

    Responsibilities:
    - Embeddings
    - Resume parsing
    - Candidate evaluation
    - Retry logic

    Other services should NEVER call the Gemini SDK directly.
    """

    DEFAULT_LLM = "gemini-2.5-flash"
    DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-2"

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY was not found in your .env file."
            )

        self.client = genai.Client(api_key=api_key)

        self.llm_model = os.getenv(
            "GEMINI_MODEL",
            self.DEFAULT_LLM,
        )

        self.embedding_model = os.getenv(
            "GEMINI_EMBEDDING_MODEL",
            self.DEFAULT_EMBEDDING_MODEL,
        )

    async def _run_with_retry(
        self,
        func: Callable[[], T],
        retries: int = 3,
        initial_delay: float = 1.0,
    ) -> T:

        delay = initial_delay

        for attempt in range(retries):
            try:
                return await asyncio.to_thread(func)

            except Exception:
                if attempt == retries - 1:
                    raise

                await asyncio.sleep(delay)
                delay *= 2

    async def generate_embeddings(
        self,
        text_chunks: List[str],
    ) -> List[List[float]]:

        if not text_chunks:
            return []

        def task():
            return self.client.models.embed_content(
                model=self.embedding_model,
                contents=text_chunks,
            )

        response = await self._run_with_retry(task)

        return [embedding.values for embedding in response.embeddings]

    async def extract_structured_profile(
        self,
        raw_resume_text: str,
    ) -> CandidateProfile:

        prompt = f"""
You are an expert technical recruiter.

Extract ONLY information present in the resume.

Never hallucinate.

Resume:

{raw_resume_text}
"""

        def task():
            return self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=CandidateProfile,
                ),
            )

        response = await self._run_with_retry(task)

        return response.parsed

    async def evaluate_candidate(
        self,
        job_description: str,
        candidate_profile: dict,
        resume_snippets: List[str],
    ) -> CandidateEvaluation:

        prompt = f"""
You are an experienced technical recruiter.

Evaluate ONLY based on the supplied information.

Return a fit score from 0-100.

Consider:
- Technical skills
- Experience
- Education
- Domain relevance
- Evidence from resume snippets

Do not hallucinate.

JOB DESCRIPTION

{job_description}

CANDIDATE PROFILE

{candidate_profile}

MATCHED RESUME SNIPPETS

{chr(10).join(resume_snippets)}
"""

        def task():
            return self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=CandidateEvaluation,
                ),
            )

        response = await self._run_with_retry(task)

        return response.parsed