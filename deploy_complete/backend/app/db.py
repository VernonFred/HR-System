import os
from functools import lru_cache
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine


@lru_cache(maxsize=1)
def get_engine():
    """Create (and cache) the SQLAlchemy engine."""
    url = os.getenv("DATABASE_URL", "sqlite:///./hr.db")
    echo = os.getenv("SQL_ECHO", "false").lower() == "true"
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=echo, connect_args=connect_args)


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLModel session for dependency injection."""
    engine = get_engine()
    with Session(engine) as session:
        yield session


def ensure_tables() -> None:
    """Create tables if they do not exist."""
    from . import models  # noqa: F401  # ensure model metadata is loaded
    from . import models_assessment  # noqa: F401  # 测评相关表

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
