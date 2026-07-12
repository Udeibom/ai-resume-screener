import os
import json
import pytest
import fitz
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient

# Set mock env variables before imports
os.environ["GEMINI_API_KEY"] = "mock-api-key"
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/resume_screener"
)
os.environ["MLFLOW_TRACKING_URI"] = ""

from app.main import app
from app.models.database import get_db, Resume, ResumeChunk
from app.services.parser import ResumeParserService
from app.services.ai_service import AIService
from app.services.pipeline import ResumeIngestionPipeline
from app.services.ranking import CandidateRankingEngine
from app.core.schemas import CandidateProfile


# Fixture to generate PDF bytes in memory
@pytest.fixture
def sample_pdf_bytes():
    doc = fitz.open()
    page = doc.new_page()
    text = """John Doe
Email: john@example.com
Skills: Python, FastAPI
Experience:
Senior Backend Developer at Tech Corp (Jan 2021 - Present)
Education:
Bachelor of Science in CS (2018-2021)
"""
    page.insert_text((50, 50), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


# Mock Database Session
class MockDbSession:
    def __init__(self):
        self.added = []
        self.flushed = False
        self.committed = False
        self.refreshed = False

    def add(self, obj):
        self.added.append(obj)
        if hasattr(obj, "id"):
            obj.id = 1

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed = True

    async def execute(self, query, params=None):
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.resume_id = 1
        mock_row.filename = "sample.pdf"
        mock_row.parsed_profile = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "skills": ["Python", "FastAPI"],
            "experience_level": "Senior",
            "work_history": [],
            "education_history": [],
        }
        mock_row.chunk_text = "Senior Backend Developer using FastAPI"
        mock_row.distance = 0.15
        mock_result.fetchall.return_value = [mock_row]
        return mock_result


# Unit test for Parser Service
def test_resume_parser_service(sample_pdf_bytes):
    # Test PDF text extraction
    extracted_text = ResumeParserService.extract_text_from_pdf(sample_pdf_bytes)
    assert "John Doe" in extracted_text
    assert "FastAPI" in extracted_text

    # Test chunking
    chunks = ResumeParserService.chunk_text(
        extracted_text, chunk_size=10, chunk_overlap=2
    )
    assert len(chunks) > 0
    assert "John Doe" in chunks[0] or "Email:" in chunks[0]


# Test Ingestion Pipeline with Mock DB and Mock AI Service
@pytest.mark.asyncio
@patch("app.services.pipeline.AIService")
async def test_resume_ingestion_pipeline(MockAIClass, sample_pdf_bytes):
    mock_ai_instance = MagicMock()
    MockAIClass.return_value = mock_ai_instance

    # Mock AI Service responses
    mock_profile = CandidateProfile(
        full_name="John Doe",
        email="john@example.com",
        skills=["Python", "FastAPI"],
        experience_level="Senior",
        work_history=[],
        education_history=[],
    )
    mock_ai_instance.extract_structured_profile = AsyncMock(return_value=mock_profile)
    mock_ai_instance.generate_embeddings = AsyncMock(return_value=[[0.1] * 3072])

    db_session = MockDbSession()
    pipeline = ResumeIngestionPipeline(db_session)

    resume = await pipeline.process_and_save_resume("sample.pdf", sample_pdf_bytes)

    assert resume.filename == "sample.pdf"
    assert db_session.flushed is True
    assert db_session.committed is True
    assert len(db_session.added) > 0


# Test Candidate Ranking Engine with Mock DB and Mock AI
@pytest.mark.asyncio
@patch("app.services.ranking.AIService")
async def test_candidate_ranking_engine(MockAIClass):
    mock_ai_instance = MagicMock()
    MockAIClass.return_value = mock_ai_instance

    mock_ai_instance.generate_embeddings = AsyncMock(return_value=[[0.1] * 3072])

    # Mock _run_with_retry for ranking
    mock_response = MagicMock()
    mock_response.text = json.dumps({"fit_score": 95, "justification": "Perfect fit"})
    mock_ai_instance._run_with_retry = AsyncMock(return_value=mock_response)
    mock_ai_instance.llm_model = "gemini-2.5-flash"
    mock_ai_instance.embedding_model = "models/gemini-embedding-2"

    db_session = MockDbSession()
    engine = CandidateRankingEngine(db_session)

    rankings = await engine.rank_candidates(
        "Looking for a FastAPI developer", limit_candidates=1
    )

    assert len(rankings) == 1
    assert rankings[0]["candidate_id"] == 1
    assert rankings[0]["name"] == "John Doe"
    assert rankings[0]["fit_score"] == 95


# Test API Endpoints
@pytest.mark.asyncio
@patch("app.services.pipeline.AIService")
@patch("app.services.ranking.AIService")
async def test_api_endpoints(MockRankingAIClass, MockPipelineAIClass, sample_pdf_bytes):
    # Setup mocks
    mock_pipeline_ai = MagicMock()
    MockPipelineAIClass.return_value = mock_pipeline_ai
    mock_profile = CandidateProfile(
        full_name="John Doe",
        email="john@example.com",
        skills=["Python", "FastAPI"],
        experience_level="Senior",
        work_history=[],
        education_history=[],
    )
    mock_pipeline_ai.extract_structured_profile = AsyncMock(return_value=mock_profile)
    mock_pipeline_ai.generate_embeddings = AsyncMock(return_value=[[0.1] * 3072])

    mock_ranking_ai = MagicMock()
    MockRankingAIClass.return_value = mock_ranking_ai
    mock_ranking_ai.generate_embeddings = AsyncMock(return_value=[[0.1] * 3072])
    mock_response = MagicMock()
    mock_response.text = json.dumps({"fit_score": 90, "justification": "Good fit"})
    mock_ranking_ai._run_with_retry = AsyncMock(return_value=mock_response)
    mock_ranking_ai.llm_model = "gemini-2.5-flash"
    mock_ranking_ai.embedding_model = "models/gemini-embedding-2"

    # Dependency override for db
    db_session = MockDbSession()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test /resumes/upload
        files = {"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")}
        response = await client.post("/api/v1/resumes/upload", files=files)
        assert response.status_code == 201
        data = response.json()
        assert data["profile"]["full_name"] == "John Doe"
        assert data["profile"]["email"] == "john@example.com"

        # 2. Test /jobs/match
        payload = {
            "job_description": "We need a Senior Python Developer with FastAPI.",
            "limit": 1,
        }
        response = await client.post("/api/v1/jobs/match", json=payload)
        assert response.status_code == 200
        match_data = response.json()
        assert len(match_data["results"]) == 1
        assert match_data["results"][0]["name"] == "John Doe"
        assert match_data["results"][0]["fit_score"] == 90

    # Clean up overrides
    app.dependency_overrides.clear()
