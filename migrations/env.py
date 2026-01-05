"""
Alembic Migration Environment

Configures how migrations are run against the database.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models so Alembic can detect them
from src.models import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object for autogenerate support
target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Get database URL from environment or Streamlit secrets.

    Priority:
    1. DATABASE_URL environment variable
    2. SUPABASE_DB_URL environment variable
    3. Construct from SUPABASE_* variables
    """
    # Direct URL
    if url := os.environ.get("DATABASE_URL"):
        return url

    if url := os.environ.get("SUPABASE_DB_URL"):
        return url

    # Construct from components
    host = os.environ.get("SUPABASE_HOST")
    port = os.environ.get("SUPABASE_PORT", "5432")
    db = os.environ.get("SUPABASE_DB", "postgres")
    user = os.environ.get("SUPABASE_USER", "postgres")
    password = os.environ.get("SUPABASE_PASSWORD")

    if host and password:
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    raise ValueError(
        "Database URL not configured. Set DATABASE_URL or SUPABASE_* environment variables."
    )


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Useful for generating SQL scripts without connecting to the database.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
