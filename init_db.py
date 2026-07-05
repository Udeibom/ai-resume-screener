import asyncio
from sqlalchemy import text
from app.models.database import engine, Base
import app.models.database as db_models  # Forces discovery of tables

async def initialize_database():
    print("Connecting to PostgreSQL and running migrations...")
    async with engine.begin() as conn:
        # 1. Enable pgvector extension in PostgreSQL
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
        # 2. Build tables matching the declarative models
        await conn.run_sync(Base.metadata.create_all)
        print("Successfully created tables: 'resumes' and 'resume_chunks'!")

if __name__ == "__main__":
    asyncio.run(initialize_database())