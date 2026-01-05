"""
Database Connection - Supabase PostgreSQL Integration
"""
import os
from typing import Generator, Optional
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# Try to import Streamlit for secrets
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


@dataclass
class DatabaseConfig:
    """Database configuration from environment or Streamlit secrets."""
    host: str = "localhost"
    port: int = 5432
    database: str = "inkassokom"
    user: str = "postgres"
    password: str = ""
    pool_size: int = 5
    max_overflow: int = 10
    ssl_mode: str = "require"

    @classmethod
    def from_streamlit_secrets(cls) -> "DatabaseConfig":
        """Load configuration from Streamlit secrets."""
        if not HAS_STREAMLIT:
            return cls.from_environment()

        try:
            secrets = st.secrets.get("supabase", {})
            if not secrets:
                # Try alternate key names
                secrets = st.secrets.get("database", {})

            if secrets:
                return cls(
                    host=secrets.get("host", secrets.get("SUPABASE_HOST", "localhost")),
                    port=int(secrets.get("port", secrets.get("SUPABASE_PORT", 5432))),
                    database=secrets.get("database", secrets.get("SUPABASE_DB", "postgres")),
                    user=secrets.get("user", secrets.get("SUPABASE_USER", "postgres")),
                    password=secrets.get("password", secrets.get("SUPABASE_PASSWORD", "")),
                    pool_size=int(secrets.get("pool_size", 5)),
                    max_overflow=int(secrets.get("max_overflow", 10)),
                    ssl_mode=secrets.get("ssl_mode", "require")
                )
        except Exception:
            pass

        return cls.from_environment()

    @classmethod
    def from_environment(cls) -> "DatabaseConfig":
        """Load configuration from environment variables."""
        database_url = os.getenv("DATABASE_URL", "")

        if database_url and database_url.startswith("postgresql"):
            # Parse DATABASE_URL
            # Format: postgresql://user:password@host:port/database
            try:
                from urllib.parse import urlparse
                parsed = urlparse(database_url)
                return cls(
                    host=parsed.hostname or "localhost",
                    port=parsed.port or 5432,
                    database=parsed.path.lstrip('/') or "inkassokom",
                    user=parsed.username or "postgres",
                    password=parsed.password or "",
                    ssl_mode=os.getenv("DATABASE_SSL_MODE", "require")
                )
            except Exception:
                pass

        # Fallback to individual env vars
        return cls(
            host=os.getenv("SUPABASE_HOST", os.getenv("DB_HOST", "localhost")),
            port=int(os.getenv("SUPABASE_PORT", os.getenv("DB_PORT", "5432"))),
            database=os.getenv("SUPABASE_DB", os.getenv("DB_NAME", "inkassokom")),
            user=os.getenv("SUPABASE_USER", os.getenv("DB_USER", "postgres")),
            password=os.getenv("SUPABASE_PASSWORD", os.getenv("DB_PASSWORD", "")),
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            ssl_mode=os.getenv("DATABASE_SSL_MODE", "require")
        )

    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string."""
        ssl_args = f"?sslmode={self.ssl_mode}" if self.ssl_mode else ""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}{ssl_args}"

    @property
    def is_configured(self) -> bool:
        """Check if database is properly configured."""
        return bool(self.host and self.password and self.host != "localhost")


# Global engine instance
_engine = None
_session_factory = None


def get_engine(config: Optional[DatabaseConfig] = None):
    """Get or create SQLAlchemy engine."""
    global _engine

    if _engine is not None:
        return _engine

    if config is None:
        config = DatabaseConfig.from_streamlit_secrets()

    if not config.is_configured:
        # Fallback to SQLite for local development
        from sqlalchemy import create_engine as ce
        _engine = ce(
            "sqlite:///./inkassokom.db",
            connect_args={"check_same_thread": False},
            echo=os.getenv("DEBUG", "false").lower() == "true"
        )
        return _engine

    _engine = create_engine(
        config.connection_string,
        poolclass=QueuePool,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_pre_ping=True,  # Check connection health
        pool_recycle=300,    # Recycle connections every 5 minutes
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )

    # Set up connection event for RLS
    @event.listens_for(_engine, "connect")
    def set_search_path(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("SET search_path TO public")
        cursor.close()

    return _engine


def get_session_factory(engine=None):
    """Get or create session factory."""
    global _session_factory

    if _session_factory is not None:
        return _session_factory

    if engine is None:
        engine = get_engine()

    _session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    return _session_factory


def get_session() -> Session:
    """Get a new database session."""
    factory = get_session_factory()
    return factory()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session as context manager with automatic commit/rollback."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(drop_all: bool = False):
    """Initialize database tables."""
    from src.models import Base

    engine = get_engine()

    if drop_all:
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    return engine


def test_connection() -> tuple[bool, str]:
    """Test database connection and return status."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return True, "Verbindung erfolgreich"
    except Exception as e:
        return False, f"Verbindungsfehler: {str(e)}"


def get_connection_info() -> dict:
    """Get connection information for display."""
    config = DatabaseConfig.from_streamlit_secrets()
    return {
        "configured": config.is_configured,
        "host": config.host if config.is_configured else "SQLite (lokal)",
        "database": config.database if config.is_configured else "inkassokom.db",
        "ssl": config.ssl_mode if config.is_configured else "N/A"
    }
