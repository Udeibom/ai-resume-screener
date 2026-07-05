import asyncio
from app.models.database import AsyncSessionLocal
from app.services.pipeline import ResumeIngestionPipeline
from app.services.ranking import CandidateRankingEngine

async def main():
    with open("sample.pdf", "rb") as f:
        mock_pdf_bytes = f.read()

    async with AsyncSessionLocal() as session:
        pipeline = ResumeIngestionPipeline(session)
        ranker = CandidateRankingEngine(session)
        
        print("--- Ingesting Mock Resume ---")
        resume = await pipeline.process_and_save_resume("sample.pdf", mock_pdf_bytes)
        print(f"Successfully processed and stored candidate record! Name: {resume.parsed_profile['full_name']}")

        print("\n--- Running Semantic Ranking Engine ---")
        job_desc = "Looking for a Senior Backend Developer proficient in Python, FastAPI, and containerization with Docker."
        
        rankings = await ranker.rank_candidates(job_desc)
        for rank in rankings:
            print(f"\nCandidate: {rank['name']} ({rank['filename']})")
            print(f"Score: {rank['fit_score']}/100")
            print(f"Justification: {rank['justification']}")

if __name__ == "__main__":
    asyncio.run(main())