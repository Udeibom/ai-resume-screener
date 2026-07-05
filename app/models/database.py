import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column,
    relationship,
)
from pgvector.sqlalchemy import Vector

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session maker for handling transactions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for all models
Base = declarative_base()

# Dependency to inject DB sessions into future API routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Gemini Embedding 2 produces 3072-dimensional vectors.
VECTOR_DIMENSIONS = 3072


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Store parsed profile info (skills, education, work experience) as JSON
    parsed_profile: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    # Relationship to access child vectors
    chunks: Mapped[List["ResumeChunk"]] = relationship(
        "ResumeChunk",
        back_populates="resume",
        cascade="all, delete-orphan",
    )


class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )

    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector column using pgvector
    embedding: Mapped[Vector] = mapped_column(
        Vector(VECTOR_DIMENSIONS),
        nullable=False,
    )

    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="chunks",
    )