from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db
from app.core.api_schemas import MatchRequest, MatchResponse, UploadResponse
from app.services.pipeline import ResumeIngestionPipeline
from app.services.ranking import CandidateRankingEngine

router = APIRouter()

@router.post(
    "/resumes/upload", 
    response_model=UploadResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a candidate resume"
)
async def upload_resume(
    file: UploadFile = File(..., description="The candidate's resume PDF file"),
    db: AsyncSession = Depends(get_db)
):
    # 1. Enforce strict file extension rules
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only standard vector PDF resumes are allowed."
        )
    
    try:
        # 2. Read file bytes asynchronously
        file_bytes = await file.read()
        
        # 3. Instantiate and run our ingestion pipeline
        pipeline = ResumeIngestionPipeline(db)
        resume_record = await pipeline.process_and_save_resume(file.filename, file_bytes)
        
        return UploadResponse(
            message="Resume successfully processed, embedded, and indexed.",
            resume_id=resume_record.id,
            filename=resume_record.filename,
            detected_candidate=resume_record.parsed_profile.get("full_name", "Unknown")
        )
    except Exception as e:
        # Production tip: Log the exact error internally, throw generic detail to client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while parsing the document: {str(e)}"
        )

@router.post(
    "/jobs/match", 
    response_model=MatchResponse,
    summary="Semantically rank parsed candidates against a job description"
)
async def match_candidates(
    payload: MatchRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Execute the RAG and LLM grading workflow
        engine = CandidateRankingEngine(db)
        rankings = await engine.rank_candidates(
            job_description=payload.job_description, 
            limit_candidates=payload.limit
        )
        
        return MatchResponse(
            job_description=payload.job_description,
            results=rankings
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile matching assessments: {str(e)}"
        )