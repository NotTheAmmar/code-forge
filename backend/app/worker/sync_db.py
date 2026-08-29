"""Synchronous SQLAlchemy engine and session factory for use in Celery workers.

Celery tasks are synchronous (non-async), so we cannot use the async engine
from `app.db`. This module provides a sync session using the psycopg2 driver.

The DATABASE_URL in settings uses `postgresql+asyncpg://` for the FastAPI app.
We swap the driver to `postgresql+psycopg2://` here for the sync context.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Convert asyncpg URL → psycopg2 URL for sync use
_sync_url = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
).replace(
    "postgresql+asyncpg:", "postgresql:"
)

# Fallback: handle plain postgresql:// URLs too
if _sync_url.startswith("postgresql+asyncpg://"):
    _sync_url = _sync_url.replace("postgresql+asyncpg://", "postgresql://")

_engine = create_engine(
    _sync_url,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=2,
)

_SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Context manager providing a synchronous DB session for Celery tasks.

    Usage::

        with get_sync_session() as session:
            submission = session.get(Submission, submission_id)
    """
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
