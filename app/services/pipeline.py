from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import Resume, ResumeChunk
from app.services.parser import ResumeParserService
from app.services.ai_service import AIService

class ResumeIngestionPipeline:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.ai = AIService()

    async def process_and_save_resume(self, filename: str, file_bytes: bytes) -> Resume:
        """
        Extracts, chunks, embeds, parses structure, and saves a resume to the database.
        """
        # 1. Extract plain text from PDF
        raw_text = ResumeParserService.extract_text_from_pdf(file_bytes)
        
        # 2. Extract structured JSON data concurrently or sequentially
        structured_profile = await self.ai.extract_structured_profile(raw_text)
        
        # 3. Slice text into searchable chunks
        text_chunks = ResumeParserService.chunk_text(raw_text, chunk_size=400, chunk_overlap=50)
        
        # 4. Generate embeddings for all text chunks
        embeddings = await self.ai.generate_embeddings(text_chunks)
        
        # 5. Assemble the core Resume record
        # Note: We dump the Pydantic schema model directly to a dictionary for the JSON column
        resume_record = Resume(
            filename=filename,
            raw_text=raw_text,
            parsed_profile=structured_profile.model_dump()
        )
        self.db.add(resume_record)
        await self.db.flush()  # Flushes to db to populate resume_record.id

        # 6. Populate the child vector chunk records
        for text_content, vector in zip(text_chunks, embeddings):
            chunk_record = ResumeChunk(
                resume_id=resume_record.id,
                chunk_text=text_content,
                embedding=vector
            )
            self.db.add(chunk_record)
            
        await self.db.commit()
        await self.db.refresh(resume_record)
        return resume_record