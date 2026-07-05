import os
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
)

# Environment

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy Base

Base = declarative_base()

# Gemini Embedding model outputs 3072-dimensional vectors.
VECTOR_DIMENSIONS = 3072

# Lazy Database Initialization

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """
    Lazily create and return the SQLAlchemy engine.

    This prevents database initialization during module import,
    making testing and CI much easier.
    """

    global _engine

    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL environment variable is not configured.")

        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )

    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """
    Lazily create the async session factory.
    """

    global _sessionmaker

    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for injecting a database session.
    """

    session_factory = get_sessionmaker()

    async with session_factory() as session:
        yield session


# ORM Models


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    parsed_profile: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    chunks: Mapped[List["ResumeChunk"]] = relationship(
        "ResumeChunk",
        back_populates="resume",
        cascade="all, delete-orphan",
    )


class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    resume_id: Mapped[int] = mapped_column(
        ForeignKey(
            "resumes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[Vector] = mapped_column(
        Vector(VECTOR_DIMENSIONS),
        nullable=False,
    )

    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="chunks",
    )
