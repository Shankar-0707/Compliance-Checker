"""
db/database.py
──────────────
Async SQLAlchemy engine and session factory.

Uses asyncpg as the PostgreSQL driver.
DATABASE_URL must be in the format:
    postgresql+asyncpg://user:password@host:port/dbname

Usage (in endpoints):
    async with get_session() as session:
        session.add(record)
        await session.commit()
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv(override=True)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ── Lazy engine singleton ─────────────────────────────────────────────────────
# Engine is created on first use rather than at import time so that
# DATABASE_URL is always read after load_dotenv() has run (important for
# Alembic's import order and for unit tests that override the env var).

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        database_url = os.environ["DATABASE_URL"]
        # Auto-correct scheme: plain postgresql:// → postgresql+asyncpg://
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Auto-correct SSL param: asyncpg uses ssl=require, not sslmode=require
        database_url = database_url.replace("sslmode=require", "ssl=require")
        _engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields a database session.

    Automatically commits on success, rolls back on exception, and always
    closes the session.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all_tables() -> None:
    """
    Create all tables defined in ORM models if they do not already exist.

    Called once at application startup for local dev.
    In production use ``alembic upgrade head`` instead.
    """
    from db import models  # noqa: F401 — registers models with Base.metadata
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
