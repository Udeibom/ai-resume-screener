import asyncio

from sqlalchemy import text

from app.models.database import Base, get_engine
import app.models.database as db_models  # Forces discovery of tables


async def initialize_database():
    print("Connecting to PostgreSQL and running migrations...")

    engine = get_engine()

    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        print("Successfully created tables: 'resumes' and 'resume_chunks'!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(initialize_database())