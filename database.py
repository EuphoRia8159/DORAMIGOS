"""AEGIS Database Engine and Session Management."""

import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from aegis_backend.config import settings

logger = logging.getLogger(__name__)

# Handle SQLite-specific connect args
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides an active database session for request scopes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables in the database if they do not exist."""
    # Import all models before create_all
    import aegis_backend.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
