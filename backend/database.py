"""Database engine, session management, and instrumentation."""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterable

from alembic import command
from alembic.config import Config
from sqlalchemy import event, inspect
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings
from core.logger import get_logger
from models import Base


settings = get_settings()
logger = get_logger(__name__)

ENGINE_ARGS = {"pool_pre_ping": True}

if settings.database_url.startswith("sqlite"):
    engine: Engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        **ENGINE_ARGS,
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        **ENGINE_ARGS,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - defensive
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependency injection."""

    with session_scope() as session:
        yield session


def _alembic_config() -> Config:
    config_path = Path(__file__).resolve().parent / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(Path(__file__).resolve().parent / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def run_migrations() -> None:
    """Apply database migrations up to the latest revision."""

    try:
        command.upgrade(_alembic_config(), "head")
    except Exception as exc:  # pragma: no cover - safety net
        logger.error("database.migration_failed", error=str(exc))
        raise


def init_db() -> None:
    """Initialize the database by running migrations or falling back to create_all."""

    try:
        run_migrations()
        logger.info("database.migrations_applied")
    except Exception:
        logger.warning("database.migrations_unavailable", action="create_all_fallback")
        Base.metadata.create_all(bind=engine)


def _format_statement(statement: str) -> str:
    return " ".join(statement.split())[:500]


def _format_identity(instance: object) -> str:
    state = inspect(instance)
    identity = state.identity
    if identity is None:
        return "<transient>"
    if len(identity) == 1:
        return str(identity[0])
    return str(identity)


SLOW_QUERY_THRESHOLD = getattr(settings, "slow_query_threshold", 0.0) or 0.0


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
    if SLOW_QUERY_THRESHOLD <= 0:
        return
    context._query_start_time = time.perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
    if SLOW_QUERY_THRESHOLD <= 0:
        return
    start = getattr(context, "_query_start_time", None)
    if start is None:
        return
    duration = time.perf_counter() - start
    if duration >= SLOW_QUERY_THRESHOLD:
        logger.warning(
            "database.slow_query",
            duration_seconds=round(duration, 6),
            statement=_format_statement(statement),
        )


@event.listens_for(Session, "after_flush")
def _audit_after_flush(session: Session, flush_context) -> None:  # noqa: ANN001
    def _log_instances(instances: Iterable[object], action: str) -> None:
        for instance in instances:
            if not isinstance(instance, Base):
                continue
            if action == "update" and not session.is_modified(instance, include_collections=False):
                continue
            logger.info(
                "database.audit",
                action=action,
                model=instance.__class__.__name__,
                identity=_format_identity(instance),
            )

    _log_instances(session.new, "insert")
    _log_instances(session.dirty, "update")
    _log_instances(session.deleted, "delete")


__all__ = [
    "engine",
    "SessionLocal",
    "session_scope",
    "get_db",
    "run_migrations",
    "init_db",
]

