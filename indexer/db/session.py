"""Database session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker

from config import Config

# Global engine instance (singleton)
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def init_db(config: Config) -> None:
    """Initialize database connection pool.

    Args:
        config: Configuration object with db_url
    """
    global _engine, _SessionLocal

    if _engine is not None:
        return  # Already initialized

    _engine = create_engine(
        config.db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,  # Set to True for SQL debugging
    )

    _SessionLocal = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_engine() -> Engine:
    """Get the global database engine.

    Returns:
        SQLAlchemy Engine instance

    Raises:
        RuntimeError: If database not initialized
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session with context manager.

    Yields:
        SQLAlchemy Session

    Example:
        with get_session() as session:
            # Use session
            pass
    """
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

