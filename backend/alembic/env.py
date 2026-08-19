"""
alembic/env.py
──────────────
Alembic migration environment — configured for async SQLAlchemy with asyncpg.

Reads DATABASE_URL from the environment so credentials are never hardcoded.
"""

import asyncio
import os
import sys
from pathlib import Path
from logging.config import fileConfig

# ── 1. Add backend root to sys.path FIRST ─────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ── 2. Load .env BEFORE importing any app modules ─────────────────────────────
from dotenv import load_dotenv  # noqa: E402
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=True)

from alembic import context  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

# ── 3. Import Base + models (for autogenerate / metadata) ─────────────────────
from db.database import Base  # noqa: E402
from db import models  # noqa: F401, E402 — registers models on Base.metadata

# Alembic config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ── 4. Build the async DATABASE_URL ──────────────────────────────────────────
_raw_url: str = os.environ["DATABASE_URL"]

# Ensure we always use the asyncpg driver (Alembic needs async for our engine)
if _raw_url.startswith("postgresql://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql+asyncpg://"):
    DATABASE_URL = _raw_url
else:
    raise ValueError(
        f"Unexpected DATABASE_URL scheme: {_raw_url!r}. "
        "Must start with postgresql:// or postgresql+asyncpg://"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL, no live connection)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async engine."""
    async_engine = create_async_engine(DATABASE_URL, echo=True)
    async with async_engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await async_engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
